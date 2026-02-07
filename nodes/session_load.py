from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple


class DirectorSessionLoad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "shots_json_path": ("STRING", {"default": "logs/director_world_YYYYMMDD_HHMMSS_shots.json"}),
                "take_index": ("INT", {"default": -1, "min": -1, "max": 9999}),  # -1 = picked
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("shot_list_json", "picked_final_prompt", "picked_notes", "picked_take_index", "take_count")
    FUNCTION = "run"
    CATEGORY = "PFN/Director"

    def run(self, shots_json_path: str, take_index: int):
        path = os.path.abspath(shots_json_path)
        if not os.path.isfile(path):
            msg = f"(file not found) {path}"
            return (msg, "", msg, -1, 0)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except Exception as e:
            msg = f"(invalid json) {path} :: {repr(e)}"
            return (msg, "", msg, -1, 0)

        takes = data.get("takes", [])
        take_count = len(takes)

        # fallback: if empty
        if take_count == 0:
            shot_list_json = json.dumps(data, ensure_ascii=False, indent=2)
            return (shot_list_json, "", "(no takes in json)", -1, 0)

        # decide which take to return
        picked_take_idx = int(data.get("picked_take_index", -1))  # might not exist
        # if user requested explicit take
        if take_index is not None and int(take_index) > 0:
            idx = int(take_index)
        else:
            # try to infer picked take:
            # 1) if a picked index exists in json
            # 2) else pick max score if present
            # 3) else last
            if picked_take_idx > 0:
                idx = picked_take_idx
            else:
                best_i = -1
                best_score = None
                for t in takes:
                    sc = t.get("score", None)
                    if sc is None:
                        continue
                    if best_score is None or sc > best_score:
                        best_score = sc
                        best_i = int(t.get("take_index") or t.get("take") or 0)
                idx = best_i if best_i > 0 else take_count

        # clamp
        if idx < 1:
            idx = 1
        if idx > take_count:
            idx = take_count

        t = takes[idx - 1]

        picked_final_prompt = str(t.get("final_prompt", ""))
        picked_notes = str(t.get("notes", "")) or str(t.get("director_notes", "")) or ""
        picked_take_index = int(t.get("take_index") or t.get("take") or idx)

        shot_list_json = json.dumps(data, ensure_ascii=False, indent=2)

        return (shot_list_json, picked_final_prompt, picked_notes, picked_take_index, take_count)
