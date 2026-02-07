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
                "lock_camera": ("BOOLEAN", {"default": True}),


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
        lock_camera: bool,
        

    ):
        w = WorldRegistry.get(world)
        if not w:
            return ("(world not found)", "", "(world not found)", seed)

        effective_seed = int(seed)

        # Custom intro index valido solo in modalità index
        idx = None
        if (custom_intro_mode == "index") and (custom_intro_index is not None) and (int(custom_intro_index) >= 0):
            idx = int(custom_intro_index)

        prompt, system_prompt, director_notes = build_prompt_from_world(
            w,
            seed=effective_seed,
            custom_intro_mode=custom_intro_mode,
            custom_intro_index=idx,
            lock_camera=lock_camera,
        )

        if include_system_prompt:
            sp = system_prompt
            # usa custom_separator se valorizzato, altrimenti preset
            sep_raw = custom_separator.strip() if custom_separator and custom_separator.strip() else separator
            sep = sep_raw.encode("utf-8").decode("unicode_escape")
            final_prompt = f"{system_prompt}{sep}{prompt}".strip() if system_prompt else prompt
        else:
            sp = ""
            final_prompt = prompt


        # Next seed (utile da collegare ad altri nodi)
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

