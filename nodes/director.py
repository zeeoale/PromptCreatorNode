from __future__ import annotations

import json
import os
import random
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any

from ..core.world_registry import WorldRegistry
from ..core.prompt_engine import build_prompt_from_world


class DirectorNode:
    def __init__(self):
        self._last: Optional[Dict[str, str]] = None

    # ======================================================
    # UI
    # ======================================================

    @classmethod
    def INPUT_TYPES(cls):
        names = WorldRegistry.list_names() or ["(no worlds found)"]

        return {
            "required": {
                "world": (names,),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
                "lock": ("BOOLEAN", {"default": False}),
                "control_after_generate": (["keep", "increment", "randomize"],),

                "custom_intro_mode": (["auto", "index", "random"],),
                "custom_intro_index": ("INT", {"default": -1, "min": -1, "max": 6}),

                "include_system_prompt": ("BOOLEAN", {"default": True}),
                "separator": (["\\n\\n", "\\n", " — ", " | ", ", "],),
                "custom_separator": ("STRING", {"default": ""}),

                "director_preset": (["custom", "continuity", "exploration", "chaos"],),

                "lock_camera": ("BOOLEAN", {"default": True}),
                "lock_lighting": ("BOOLEAN", {"default": True}),
                "lock_outfit": ("BOOLEAN", {"default": True}),
                "lock_pose": ("BOOLEAN", {"default": False}),

                "freeze_mode": (["off", "freeze", "refresh"],),
                "freeze_scope": (["all", "camera_lighting", "camera", "none"],),
                "change_one": ([
                    "none", "camera", "lighting", "outfit", "pose",
                    "expression", "background", "objects",
                    "atmosphere", "accessory", "custom_intro",
                ],),

                # R8
                "take_count": ("INT", {"default": 1, "min": 1, "max": 16}),
                "take_seed_mode": (["keep", "increment", "randomize"],),

                # R9
                "pick_mode": (["off", "best_take"],),
                "pick_rule": (["balanced", "closeup", "lowlight", "profile", "keyword"],),
                "pick_keyword": ("STRING", {"default": "close-up"}),

                # R10
                "json_pretty": ("BOOLEAN", {"default": True}),

                # R11
                "save_to_file": ("BOOLEAN", {"default": False}),
                "save_format": (["json", "json+txt"],),
                "save_dir": ("STRING", {"default": "logs"}),
                "save_prefix": ("STRING", {"default": "director"}),
            }
        }

    RETURN_TYPES = (
        "STRING", "STRING", "STRING", "STRING", "INT",
        "STRING", "STRING", "STRING", "INT",
        "STRING", "STRING"
    )

    RETURN_NAMES = (
        "prompt",
        "system_prompt",
        "final_prompt",
        "director_notes",
        "next_seed",
        "shot_list",
        "picked_final_prompt",
        "picked_notes",
        "picked_take_index",
        "shot_list_json",
        "picked_json",
    )

    FUNCTION = "run"
    CATEGORY = "PFN/Director"

    # ======================================================
    # HELPERS
    # ======================================================

    def _dump_json(self, obj: Any, pretty: bool) -> str:
        return json.dumps(
            obj,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )

    def _make_separator(self, separator: str, custom: str) -> str:
        raw = custom.strip() if custom.strip() else separator
        return raw.encode("utf-8").decode("unicode_escape")

    def _compute_next_seed(self, seed: int, lock: bool, mode: str) -> int:
        if lock:
            return seed
        if mode == "increment":
            return (seed + 1) % (2**31)
        if mode == "randomize":
            return random.randint(0, 2**31 - 1)
        return seed

    def _apply_preset(
        self,
        preset: str,
        lock_camera: bool,
        lock_lighting: bool,
        lock_outfit: bool,
        lock_pose: bool,
    ) -> Tuple[str, bool, bool, bool, bool]:
        p = (preset or "custom").lower()
        if p == "continuity":
            return p, True, True, True, False
        if p == "exploration":
            return p, True, False, False, False
        if p == "chaos":
            return p, False, False, False, False
        return "custom", lock_camera, lock_lighting, lock_outfit, lock_pose

    def _filter_overrides(self, data: Dict[str, str], scope: str) -> Dict[str, str]:
        if scope == "none":
            return {}
        if scope == "camera":
            keys = {"camera"}
        elif scope == "camera_lighting":
            keys = {"camera", "lighting"}
        else:
            keys = set(data.keys())
        return {k: v for k, v in data.items() if k in keys}

    def _score_take(
        self,
        rule: str,
        keyword: str,
        chosen: Dict[str, str],
        final_prompt: str,
    ) -> int:
        cam = chosen.get("camera", "").lower()
        light = chosen.get("lighting", "").lower()
        score = 0

        if rule == "closeup" and any(x in cam for x in ["close", "85mm", "105mm"]):
            score += 10
        if rule == "lowlight" and any(x in light for x in ["low", "dark", "shadow"]):
            score += 10
        if rule == "profile" and "profile" in cam:
            score += 10
        if rule == "keyword":
            score += final_prompt.lower().count(keyword.lower()) * 10

        if rule == "balanced":
            if "portrait" in cam:
                score += 5
            if "low" in light:
                score += 5

        return score

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        world, seed, lock, control_after_generate,
        custom_intro_mode, custom_intro_index,
        include_system_prompt, separator, custom_separator,
        director_preset,
        lock_camera, lock_lighting, lock_outfit, lock_pose,
        freeze_mode, freeze_scope, change_one,
        take_count, take_seed_mode,
        pick_mode, pick_rule, pick_keyword,
        json_pretty,
        save_to_file, save_format, save_dir, save_prefix,
    ):
        w = WorldRegistry.get(world)
        if not w:
            return ("(world not found)", "", "", "", seed, "", "", "", -1, "{}", "{}")

        preset, lock_camera, lock_lighting, lock_outfit, lock_pose = \
            self._apply_preset(director_preset, lock_camera, lock_lighting, lock_outfit, lock_pose)

        sep = self._make_separator(separator, custom_separator)
        fm = freeze_mode.lower()
        fs = freeze_scope.lower()
        co = change_one.lower()

        shot_list = []
        takes_json = []

        best_score = -1_000_000
        best_take = -1
        best_prompt = ""
        best_notes = ""
        best_chosen = {}

        current_seed = seed
        last_prompt = ""
        last_system_prompt = ""
        last_final_prompt = ""
        last_notes = ""
        best_prompt = ""
        best_notes = ""
        best_take = -1

        for i in range(take_count):
            overrides = None
            if fm == "freeze" and self._last:
                overrides = self._filter_overrides(self._last, fs)
                if co != "none":
                    overrides.pop(co, None)

            prompt, system_prompt, notes, chosen = build_prompt_from_world(
                w,
                seed=current_seed,
                custom_intro_mode=custom_intro_mode,
                custom_intro_index=custom_intro_index if custom_intro_index >= 0 else None,
                lock_camera=lock_camera,
                lock_lighting=lock_lighting,
                lock_outfit=lock_outfit,
                lock_pose=lock_pose,
                overrides=overrides,
            )

            final_prompt = f"{system_prompt}{sep}{prompt}".strip() if include_system_prompt else prompt
            last_prompt = prompt
            last_system_prompt = system_prompt
            last_final_prompt = final_prompt
            last_notes = notes

            if fm in ("off", "refresh") or (fm == "freeze" and co != "none"):
                self._last = dict(chosen)

            score = None
            if pick_mode == "best_take":
                score = self._score_take(pick_rule, pick_keyword, chosen, final_prompt)
                if score > best_score:
                    best_score = score
                    best_take = i + 1
                    best_prompt = final_prompt
                    best_notes = notes
                    best_chosen = dict(chosen)

            shot_list.append(f"===== TAKE {i+1} =====\n{final_prompt}")
            takes_json.append({
                "take": i + 1,
                "seed": current_seed,
                "chosen": chosen,
                "final_prompt": final_prompt,
                "score": score,
            })

            current_seed = self._compute_next_seed(current_seed, lock, take_seed_mode)

        shot_list_text = "\n\n".join(shot_list)
        shot_list_json = self._dump_json({"takes": takes_json}, json_pretty)
        picked_json = self._dump_json({
            "picked_take": best_take,
            "picked_prompt": best_prompt,
            "picked_chosen": best_chosen,
            "score": best_score,
        }, json_pretty)

        if save_to_file:
            print("[Director][R11] save_to_file =", save_to_file, "save_dir =", save_dir, "save_format =", save_format, "save_prefix =", save_prefix)
            print("[Director][R11] cwd =", os.getcwd())
            print("[Director][R11] abs(save_dir) =", os.path.abspath(save_dir))
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = os.path.abspath(save_dir)
            print("[Director][R11] creating dir:", out_dir)
            os.makedirs(out_dir, exist_ok=True)
            print("[Director][R11] dir exists:", os.path.isdir(out_dir))

            base = f"{save_prefix}_{world}_{ts}".replace(" ", "_")
            json_path = os.path.join(out_dir, base + "_shots.json")
            picked_path = os.path.join(out_dir, base + "_picked.json")

            print("[Director][R11] writing:", json_path)
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(shot_list_json)

            print("[Director][R11] writing:", picked_path)
            with open(picked_path, "w", encoding="utf-8") as f:
                f.write(picked_json)

            if save_format == "json+txt":
                txt_path = os.path.join(out_dir, base + "_shots.txt")
                print("[Director][R11] writing:", txt_path)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(shot_list_text)

            print("[Director][R11] DONE ✅")
        except Exception as e:
            print("[Director][R11] ERROR ❌", repr(e))
            os.makedirs(save_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"{save_prefix}_{world}_{ts}".replace(" ", "_")
            with open(os.path.join(save_dir, base + "_shots.json"), "w", encoding="utf-8") as f:
                f.write(shot_list_json)
            with open(os.path.join(save_dir, base + "_picked.json"), "w", encoding="utf-8") as f:
                f.write(picked_json)
            if save_format == "json+txt":
                with open(os.path.join(save_dir, base + "_shots.txt"), "w", encoding="utf-8") as f:
                    f.write(shot_list_text)

        next_seed = self._compute_next_seed(seed, lock, control_after_generate)

        return (
        last_prompt,
        last_system_prompt if include_system_prompt else "",
        last_final_prompt,
        last_notes,
        next_seed,
        shot_list_text,
        best_prompt if best_prompt else last_final_prompt,
        best_notes if best_notes else last_notes,
        best_take if best_take != -1 else take_count,
        shot_list_json,
        picked_json,
)
