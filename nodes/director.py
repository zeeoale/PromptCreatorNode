from __future__ import annotations

import random
from typing import Dict, Optional, List, Tuple

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

                # --- R8: Shot List ---
                "take_count": ("INT", {"default": 1, "min": 1, "max": 16}),
                "take_seed_mode": (["keep", "increment", "randomize"],),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("prompt", "system_prompt", "final_prompt", "director_notes", "next_seed", "shot_list")
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
        else:  # "all"
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
    ):
        w = WorldRegistry.get(world)
        if not w:
            return ("(world not found)", "", "(world not found)", "", seed, "(world not found)")

        # --- validate / normalize ---
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

        # --- generate N takes ---
        shot_blocks: List[str] = []
        current_seed = effective_seed

        last_prompt = ""
        last_system_prompt = ""
        last_final_prompt = ""
        last_notes = ""
        last_next_seed = current_seed

        for i in range(take_count):
            # freeze overrides (from memory) + change_one
            overrides: Optional[Dict[str, str]] = None
            applied_overrides: Dict[str, str] = {}

            if fm == "freeze" and self._last:
                applied_overrides = self._filter_overrides(self._last, fs)

                # change only one => remove that key from overrides
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

            # update memory logic
            if fm in ("off", "refresh"):
                self._last = dict(chosen)
            elif fm == "freeze" and co != "none":
                # when changing one, the new take becomes the new base
                self._last = dict(chosen)

            # final prompt
            if include_system_prompt:
                sp_out = system_prompt
                final_prompt = f"{system_prompt}{sep}{prompt}".strip() if system_prompt else prompt
            else:
                sp_out = ""
                final_prompt = prompt

            applied_keys = ", ".join(sorted(applied_overrides.keys())) if applied_overrides else "(none)"
            header = (
                f"preset: {preset}\n"
                f"freeze_mode: {fm}\n"
                f"freeze_scope: {fs}\n"
                f"change_one: {co}\n"
                f"applied_overrides: {applied_keys}\n"
                f"take: {i + 1}/{take_count}\n"
                f"seed: {current_seed}\n"
            )
            notes_out = (header + director_notes).strip()

            # save last outputs (for node outputs)
            last_prompt = prompt
            last_system_prompt = sp_out
            last_final_prompt = final_prompt
            last_notes = notes_out

            # shot list block
            shot_blocks.append(
                "\n".join([
                    f"===== TAKE {i + 1}/{take_count} =====",
                    notes_out,
                    "----- FINAL PROMPT -----",
                    final_prompt,
                    "",
                ]).strip()
            )

            # compute seed for next take
            # (se lock=True, resta fermo; altrimenti segue take_seed_mode)
            current_seed = self._compute_next_seed(current_seed, lock, take_seed_mode)

        # next_seed for node output should match the same rule of "control_after_generate"
        last_next_seed = self._compute_next_seed(effective_seed, lock, control_after_generate)

        shot_list = "\n\n".join(shot_blocks).strip()

        return (last_prompt, last_system_prompt, last_final_prompt, last_notes, last_next_seed, shot_list)
