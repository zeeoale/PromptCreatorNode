from __future__ import annotations

import random

from ..core.world_registry import WorldRegistry
from ..core.prompt_engine import build_prompt_from_world


class DirectorNode:
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
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("prompt", "system_prompt", "final_prompt", "director_notes", "next_seed")
    FUNCTION = "run"
    CATEGORY = "PFN/Director"

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
    ):
        w = WorldRegistry.get(world)
        if not w:
            return ("(world not found)", "", "(world not found)", "", seed)

        effective_seed = int(seed)

        # --- custom intro index valido solo se mode=index ---
        idx = None
        if (custom_intro_mode == "index") and (custom_intro_index is not None) and (int(custom_intro_index) >= 0):
            idx = int(custom_intro_index)

        # --- preset (logica UI: qui è il posto giusto) ---
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

        # --- build prompt ---
        prompt, system_prompt, director_notes = build_prompt_from_world(
            w,
            seed=effective_seed,
            custom_intro_mode=custom_intro_mode,
            custom_intro_index=idx,
            lock_camera=lock_camera,
            lock_lighting=lock_lighting,
            lock_outfit=lock_outfit,
            lock_pose=lock_pose,
        )

        # prepend preset to notes (sempre utile)
        director_notes = f"preset: {preset}\n{director_notes}".strip() if director_notes else f"preset: {preset}"

        # --- final prompt formatting ---
        if include_system_prompt:
            sp = system_prompt
            sep_raw = custom_separator.strip() if custom_separator and custom_separator.strip() else separator
            sep = sep_raw.encode("utf-8").decode("unicode_escape")
            final_prompt = f"{system_prompt}{sep}{prompt}".strip() if system_prompt else prompt
        else:
            sp = ""
            final_prompt = prompt

        # --- next seed ---
        if lock:
            next_seed = effective_seed
        else:
            mode = (control_after_generate or "keep").lower().strip()
            if mode == "increment":
                next_seed = (effective_seed + 1) % (2**31)
            elif mode == "randomize":
                next_seed = random.randint(0, 2**31 - 1)
            else:
                next_seed = effective_seed

        return (prompt, sp, final_prompt, director_notes, next_seed)
