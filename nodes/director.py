from __future__ import annotations

import json
import random
from typing import Dict, Optional, List, Tuple, Any

from ..core.world_registry import WorldRegistry
from ..core.prompt_engine import build_prompt_from_world


class DirectorNode:
    def __init__(self):
        self._last: Optional[Dict[str, str]] = None

    @classmethod
    def INPUT_TYPES(cls):
        names = WorldRegistry.list_names()
        if not names:
            names = ["(no worlds found)"]

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
                    "none",
                    "camera",
                    "lighting",
                    "outfit",
                    "pose",
                    "expression",
                    "background",
                    "objects",
                    "atmosphere",
                    "accessory",
                    "custom_intro",
                ],),

                # R8: Shot List
                "take_count": ("INT", {"default": 1, "min": 1, "max": 16}),
                "take_seed_mode": (["keep", "increment", "randomize"],),

                # R9: Best Take Picker
                "pick_mode": (["off", "best_take"],),
                "pick_rule": (["balanced", "closeup", "lowlight", "profile", "keyword"],),
                "pick_keyword": ("STRING", {"default": "close-up"}),

                # R10: JSON export
                "json_pretty": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT", "STRING", "STRING", "STRING", "INT", "STRING", "STRING")
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

    def _filter_overrides(self, data: Dict[str, str], scope: str) -> Dict[str, str]:
        scope = (scope or "all").lower().strip()
        if scope == "none":
            return {}
        if scope == "camera":
            keys = {"camera"}
        elif scope == "camera_lighting":
            keys = {"camera", "lighting"}
        else:
            keys = set(data.keys())
        return {k: v for k, v in data.items() if k in keys and v and str(v).strip()}

    def _apply_preset(
        self,
        director_preset: str,
        lock_camera: bool,
        lock_lighting: bool,
        lock_outfit: bool,
        lock_pose: bool,
    ) -> Tuple[str, bool, bool, bool, bool]:
        preset = (director_preset or "custom").lower().strip()
        if preset != "custom":
            if preset == "continuity":
                lock_camera = True
                lock_lighting = True
                lock_outfit = True
                lock_pose = False
            elif preset == "exploration":
                lock_camera = True
                lock_lighting = False
                lock_outfit = False
                lock_pose = False
            elif preset == "chaos":
                lock_camera = False
                lock_lighting = False
                lock_outfit = False
                lock_pose = False
        return preset, lock_camera, lock_lighting, lock_outfit, lock_pose

    def _make_separator(self, separator: str, custom_separator: str) -> str:
        sep_raw = custom_separator.strip() if custom_separator and custom_separator.strip() else separator
        return sep_raw.encode("utf-8").decode("unicode_escape")

    def _compute_next_seed(self, seed: int, lock: bool, mode: str) -> int:
        if lock:
            return seed
        mode = (mode or "keep").lower().strip()
        if mode == "increment":
            return (seed + 1) % (2**31)
        if mode == "randomize":
            return random.randint(0, 2**31 - 1)
        return seed

    def _score_take(
        self,
        rule: str,
        keyword: str,
        chosen: Dict[str, str],
        final_prompt: str,
    ) -> int:
        rule = (rule or "balanced").lower().strip()
        kw = (keyword or "").lower().strip()

        cam = (chosen.get("camera") or "").lower()
        light = (chosen.get("lighting") or "").lower()

        def has_any(text: str, needles: List[str]) -> bool:
            return any(n in text for n in needles)

        score = 0

        if rule == "closeup":
            if has_any(cam, ["close", "85mm", "105mm", "portrait", "tight"]):
                score += 10
            if "24mm" in cam:
                score -= 2

        elif rule == "lowlight":
            if has_any(light, ["low", "dim", "candle", "noir", "shadow", "dark"]):
                score += 10
            if has_any(light, ["bright", "daylight", "high key"]):
                score -= 3

        elif rule == "profile":
            if "profile" in cam:
                score += 10
            if has_any(cam, ["frontal", "centered frontal"]):
                score -= 1

        elif rule == "keyword":
            if kw:
                score += final_prompt.lower().count(kw) * 10

        else:  # balanced
            if has_any(cam, ["close", "portrait", "85mm", "105mm"]):
                score += 5
            if has_any(light, ["low", "shadow", "noir", "candle", "dim"]):
                score += 5

        return score

    def _dump_json(self, obj: Any, pretty: bool) -> str:
        if pretty:
            return json.dumps(obj, ensure_ascii=False, indent=2)
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    def run(
        self,
        world: str,
        seed: int,
        lock: bool,
        control_after_generate: str,
        custom_intro_mode: str,
        custom_intro_index: int,
        include_system_prompt: bool,
        separator: str,
        custom_separator: str,
        director_preset: str,
        lock_camera: bool,
        lock_lighting: bool,
        lock_outfit: bool,
        lock_pose: bool,
        freeze_mode: str,
        freeze_scope: str,
        change_one: str,
        take_count: int,
        take_seed_mode: str,
        pick_mode: str,
        pick_rule: str,
        pick_keyword: str,
        json_pretty: bool,
    ):
        w = WorldRegistry.get(world)
        if not w:
            return ("(world not found)", "", "(world not found)", "", seed, "(world not found)", "", "", -1, "{}", "{}")

        effective_seed = int(seed)
        take_count = int(take_count)

        idx = None
        if (custom_intro_mode == "index") and (custom_intro_index is not None) and (int(custom_intro_index) >= 0):
            idx = int(custom_intro_index)

        preset, lock_camera, lock_lighting, lock_outfit, lock_pose = self._apply_preset(
            director_preset, lock_camera, lock_lighting, lock_outfit, lock_pose
        )

        fm = (freeze_mode or "off").lower().strip()
        fs = (freeze_scope or "all").lower().strip()
        co = (change_one or "none").lower().strip()
        sep = self._make_separator(separator, custom_separator)

        # best take tracking
        best_score = -10**9
        best_take_idx = -1
        best_final_prompt = ""
        best_notes = ""
        best_chosen: Dict[str, str] = {}
        best_seed = effective_seed

        # last take outputs
        last_prompt = ""
        last_system_prompt = ""
        last_final_prompt = ""
        last_notes = ""

        shot_blocks: List[str] = []
        takes_json: List[Dict[str, Any]] = []

        current_seed = effective_seed

        for i in range(take_count):
            overrides: Optional[Dict[str, str]] = None
            applied_overrides: Dict[str, str] = {}

            if fm == "freeze" and self._last:
                applied_overrides = self._filter_overrides(self._last, fs)
                if co != "none" and co in applied_overrides:
                    applied_overrides.pop(co, None)
                overrides = dict(applied_overrides) if applied_overrides else None
            elif fm == "refresh":
                overrides = None
            else:
                overrides = None

            prompt, system_prompt, director_notes, chosen = build_prompt_from_world(
                w,
                seed=current_seed,
                custom_intro_mode=custom_intro_mode,
                custom_intro_index=idx,
                lock_camera=lock_camera,
                lock_lighting=lock_lighting,
                lock_outfit=lock_outfit,
                lock_pose=lock_pose,
                overrides=overrides,
            )

            # memory update
            if fm in ("off", "refresh"):
                self._last = dict(chosen)
            elif fm == "freeze" and co != "none":
                self._last = dict(chosen)

            # final prompt
            if include_system_prompt:
                sp_out = system_prompt
                final_prompt = f"{system_prompt}{sep}{prompt}".strip() if system_prompt else prompt
            else:
                sp_out = ""
                final_prompt = prompt

            applied_keys = sorted(applied_overrides.keys()) if applied_overrides else []
            header = (
                f"preset: {preset}\n"
                f"freeze_mode: {fm}\n"
                f"freeze_scope: {fs}\n"
                f"change_one: {co}\n"
                f"applied_overrides: {', '.join(applied_keys) if applied_keys else '(none)'}\n"
                f"take: {i + 1}/{take_count}\n"
                f"seed: {current_seed}\n"
            )
            notes_out = (header + director_notes).strip()

            # score
            picker_on = (pick_mode or "off").lower().strip() == "best_take"
            score = self._score_take(pick_rule, pick_keyword, chosen, final_prompt) if picker_on else None

            # best take
            if picker_on and score is not None and score > best_score:
                best_score = score
                best_take_idx = i + 1
                best_final_prompt = final_prompt
                best_notes = (notes_out + f"\nscore: {score}").strip()
                best_chosen = dict(chosen)
                best_seed = current_seed

            # save last
            last_prompt = prompt
            last_system_prompt = sp_out
            last_final_prompt = final_prompt
            last_notes = notes_out

            shot_blocks.append(
                "\n".join([
                    f"===== TAKE {i + 1}/{take_count} =====",
                    notes_out + (f"\nscore: {score}" if score is not None else ""),
                    "----- FINAL PROMPT -----",
                    final_prompt,
                    "",
                ]).strip()
            )

            takes_json.append({
                "take_index": i + 1,
                "seed": current_seed,
                "preset": preset,
                "freeze_mode": fm,
                "freeze_scope": fs,
                "change_one": co,
                "applied_overrides": applied_keys,
                "chosen": dict(chosen),
                "prompt": prompt,
                "system_prompt": system_prompt if include_system_prompt else "",
                "final_prompt": final_prompt,
                "notes": notes_out,
                "score": score,
            })

            current_seed = self._compute_next_seed(current_seed, lock, take_seed_mode)

        # next seed for node output
        next_seed = self._compute_next_seed(effective_seed, lock, control_after_generate)

        shot_list = "\n\n".join(shot_blocks).strip()

        # picker off => pick last
        picker_on = (pick_mode or "off").lower().strip() == "best_take"
        if not picker_on:
            best_take_idx = take_count
            best_final_prompt = last_final_prompt
            best_notes = (last_notes + "\nscore: (picker off)").strip()
            best_chosen = takes_json[-1]["chosen"] if takes_json else {}
            best_seed = takes_json[-1]["seed"] if takes_json else effective_seed

        shot_list_json_obj = {
            "world": world,
            "take_count": take_count,
            "seed_start": effective_seed,
            "take_seed_mode": (take_seed_mode or "keep"),
            "include_system_prompt": bool(include_system_prompt),
            "separator": self._make_separator(separator, custom_separator),
            "picker": {
                "mode": (pick_mode or "off"),
                "rule": (pick_rule or "balanced"),
                "keyword": (pick_keyword or ""),
            },
            "takes": takes_json,
        }

        picked_json_obj = {
            "picked_take_index": int(best_take_idx),
            "picked_seed": int(best_seed),
            "picked_score": (int(best_score) if picker_on else None),
            "picked_chosen": best_chosen,
            "picked_final_prompt": best_final_prompt,
            "picked_notes": best_notes,
        }

        shot_list_json = self._dump_json(shot_list_json_obj, bool(json_pretty))
        picked_json = self._dump_json(picked_json_obj, bool(json_pretty))

        return (
            last_prompt,
            last_system_prompt,
            last_final_prompt,
            last_notes,
            int(next_seed),
            shot_list,
            best_final_prompt,
            best_notes,
            int(best_take_idx),
            shot_list_json,
            picked_json,
        )
