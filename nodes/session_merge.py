from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional


class DirectorSessionMerge:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # percorsi separati da newline (più comodo di una lista UI)
                "shots_json_paths": ("STRING", {"default": "logs/a_shots.json\nlogs/b_shots.json"}),
                "pretty_json": ("BOOLEAN", {"default": True}),
                "recompute_picked": ("BOOLEAN", {"default": True}),
                "save_merged": ("BOOLEAN", {"default": False}),
                "save_dir": ("STRING", {"default": "logs"}),
                "save_prefix": ("STRING", {"default": "director_merge"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("merged_shot_list_json", "merged_picked_json", "merged_take_count", "picked_take_index")
    FUNCTION = "run"
    CATEGORY = "PFN/Director"

    def _dump(self, obj: Any, pretty: bool) -> str:
        if pretty:
            return json.dumps(obj, ensure_ascii=False, indent=2)
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    def _load_json(self, path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        p = os.path.abspath(path.strip())
        if not p or not os.path.isfile(p):
            return None, f"(file not found) {p}"
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), None
        except Exception as e:
            return None, f"(invalid json) {p} :: {repr(e)}"

    def _best_take_by_score(self, takes: List[Dict[str, Any]]) -> Tuple[int, Optional[int]]:
        # return (index1based, score or None)
        best_i = 1
        best_score: Optional[int] = None
        for i, t in enumerate(takes, start=1):
            sc = t.get("score", None)
            if sc is None:
                continue
            try:
                sc_int = int(sc)
            except Exception:
                continue
            if best_score is None or sc_int > best_score:
                best_score = sc_int
                best_i = i
        return best_i, best_score

    def run(
        self,
        shots_json_paths: str,
        pretty_json: bool,
        recompute_picked: bool,
        save_merged: bool,
        save_dir: str,
        save_prefix: str,
    ):
        raw = shots_json_paths or ""
        raw = raw.replace("\n", ";")
        paths = [p.strip() for p in raw.split(";") if p.strip() and not p.strip().startswith("#")]


        if not paths:
            msg = "(no paths provided)"
            return (msg, "{}", 0, -1)

        merged_takes: List[Dict[str, Any]] = []
        load_errors: List[str] = []

        # Keep some top-level info (best effort)
        meta_worlds: List[str] = []
        meta_files: List[str] = []

        for path in paths:
            data, err = self._load_json(path)
            if err:
                load_errors.append(err)
                continue

            assert data is not None
            takes = data.get("takes", [])
            if not isinstance(takes, list):
                load_errors.append(f"(bad takes array) {path}")
                continue

            meta_worlds.append(str(data.get("world", "")) if "world" in data else "")
            meta_files.append(os.path.abspath(path))

            for t in takes:
                if not isinstance(t, dict):
                    continue
                merged_takes.append({
                    **t,
                    "source_file": os.path.abspath(path),
                })

        # If nothing loaded
        if not merged_takes:
            msg = "(no takes loaded)\n" + "\n".join(load_errors[:50])
            return (msg, "{}", 0, -1)

        # Re-number takes + normalize key name
        for i, t in enumerate(merged_takes, start=1):
            t["take_index"] = i

        take_count = len(merged_takes)

        # Compute picked
        picked_idx = 1
        picked_score: Optional[int] = None
        if recompute_picked:
            picked_idx, picked_score = self._best_take_by_score(merged_takes)

        picked_take = merged_takes[picked_idx - 1]
        picked_json_obj = {
            "picked_take_index": int(picked_idx),
            "picked_score": picked_score,
            "picked_seed": picked_take.get("seed", None),
            "picked_source_file": picked_take.get("source_file", ""),
            "picked_chosen": picked_take.get("chosen", {}),
            "picked_final_prompt": picked_take.get("final_prompt", ""),
            "picked_notes": picked_take.get("notes", ""),
        }

        merged_json_obj: Dict[str, Any] = {
            "type": "PFN_Director_MergedSession",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source_files": meta_files,
            "worlds": [w for w in meta_worlds if w],
            "take_count": take_count,
            "takes": merged_takes,
        }

        # Append errors (useful in debug)
        if load_errors:
            merged_json_obj["load_errors"] = load_errors

        merged_shot_list_json = self._dump(merged_json_obj, bool(pretty_json))
        merged_picked_json = self._dump(picked_json_obj, bool(pretty_json))

        # Optional save
        if save_merged:
            out_dir = os.path.abspath(save_dir)
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"{save_prefix}_{ts}".replace(" ", "_")

            merged_path = os.path.join(out_dir, base + "_merged_shots.json")
            picked_path = os.path.join(out_dir, base + "_merged_picked.json")

            with open(merged_path, "w", encoding="utf-8") as f:
                f.write(merged_shot_list_json)

            with open(picked_path, "w", encoding="utf-8") as f:
                f.write(merged_picked_json)

        return (merged_shot_list_json, merged_picked_json, int(take_count), int(picked_idx))
