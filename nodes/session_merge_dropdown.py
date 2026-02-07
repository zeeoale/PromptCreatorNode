from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _dump(obj: Any, pretty: bool) -> str:
    if pretty:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _safe_listdir(path: str) -> List[str]:
    try:
        return os.listdir(path)
    except Exception:
        return []


def _collect_shots_files(logs_dir: str) -> List[str]:
    # Mostra solo *_shots.json
    files = [
        f for f in _safe_listdir(logs_dir)
        if f.endswith("_shots.json") and os.path.isfile(os.path.join(logs_dir, f))
    ]
    files.sort()
    return files


def _load_json(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    p = os.path.abspath(path)
    if not os.path.isfile(p):
        return None, f"(file not found) {p}"
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, f"(invalid json) {p} :: {repr(e)}"


def _best_take_by_score(takes: List[Dict[str, Any]]) -> Tuple[int, Optional[int]]:
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


class DirectorSessionMergeDropdown:
    """
    Merge di 2 sessioni salvate (_shots.json) selezionandole da dropdown.
    I dropdown vengono popolati scansionando logs_dir al momento del reload (tasto R).
    """

    @classmethod
    def INPUT_TYPES(cls):
        logs_dir_default = "logs"
        logs_dir = os.path.abspath(logs_dir_default)
        files = _collect_shots_files(logs_dir)

        if not files:
            files = ["(no sessions found)"]

        return {
            "required": {
                "logs_dir": ("STRING", {"default": logs_dir_default}),
                "json1": (files,),
                "json2": (files,),
                "pretty_json": ("BOOLEAN", {"default": True}),
                "recompute_picked": ("BOOLEAN", {"default": True}),
                "save_merged": ("BOOLEAN", {"default": False}),
                "save_prefix": ("STRING", {"default": "director_merge"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("merged_shot_list_json", "merged_picked_json", "merged_take_count", "picked_take_index")
    FUNCTION = "run"
    CATEGORY = "PFN/Director"

    def run(
        self,
        logs_dir: str,
        json1: str,
        json2: str,
        pretty_json: bool,
        recompute_picked: bool,
        save_merged: bool,
        save_prefix: str,
    ):
        logs_dir_abs = os.path.abspath(logs_dir.strip() or "logs")

        # Se la lista non era disponibile all'INPUT_TYPES, qui gestiamo comunque
        if json1 == "(no sessions found)" or json2 == "(no sessions found)":
            msg = f"(no sessions found in logs_dir) {logs_dir_abs}"
            return (msg, "{}", 0, -1)

        path1 = os.path.join(logs_dir_abs, json1)
        path2 = os.path.join(logs_dir_abs, json2)

        data1, err1 = _load_json(path1)
        data2, err2 = _load_json(path2)

        load_errors: List[str] = []
        if err1:
            load_errors.append(err1)
        if err2:
            load_errors.append(err2)

        if data1 is None or data2 is None:
            msg = "(load failed)\n" + "\n".join(load_errors)
            return (msg, "{}", 0, -1)

        takes1 = data1.get("takes", [])
        takes2 = data2.get("takes", [])

        if not isinstance(takes1, list):
            takes1 = []
            load_errors.append(f"(bad takes array) {os.path.abspath(path1)}")
        if not isinstance(takes2, list):
            takes2 = []
            load_errors.append(f"(bad takes array) {os.path.abspath(path2)}")

        merged_takes: List[Dict[str, Any]] = []

        def add_takes(takes: List[Dict[str, Any]], source_file: str):
            for t in takes:
                if not isinstance(t, dict):
                    continue
                merged_takes.append({**t, "source_file": source_file})

        add_takes(takes1, os.path.abspath(path1))
        add_takes(takes2, os.path.abspath(path2))

        if not merged_takes:
            msg = "(no takes loaded)\n" + "\n".join(load_errors)
            return (msg, "{}", 0, -1)

        # rinumera take_index
        for i, t in enumerate(merged_takes, start=1):
            t["take_index"] = i

        take_count = len(merged_takes)

        # picked
        picked_idx = 1
        picked_score: Optional[int] = None
        if recompute_picked:
            picked_idx, picked_score = _best_take_by_score(merged_takes)

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
            "logs_dir": logs_dir_abs,
            "source_files": [os.path.abspath(path1), os.path.abspath(path2)],
            "worlds": [
                str(data1.get("world", "")) if "world" in data1 else "",
                str(data2.get("world", "")) if "world" in data2 else "",
            ],
            "take_count": take_count,
            "takes": merged_takes,
        }

        if load_errors:
            merged_json_obj["load_errors"] = load_errors

        merged_shot_list_json = _dump(merged_json_obj, bool(pretty_json))
        merged_picked_json = _dump(picked_json_obj, bool(pretty_json))

        # save
        if save_merged:
            os.makedirs(logs_dir_abs, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"{save_prefix}_{ts}".replace(" ", "_")
            out_merged = os.path.join(logs_dir_abs, base + "_merged_shots.json")
            out_picked = os.path.join(logs_dir_abs, base + "_merged_picked.json")

            with open(out_merged, "w", encoding="utf-8") as f:
                f.write(merged_shot_list_json)

            with open(out_picked, "w", encoding="utf-8") as f:
                f.write(merged_picked_json)

        return (merged_shot_list_json, merged_picked_json, int(take_count), int(picked_idx))
