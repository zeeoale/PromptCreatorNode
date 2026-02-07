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
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("prompt", "system_prompt", "next_seed")
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
    ):
        w = WorldRegistry.get(world)
        if not w:
            return ("(world not found)", "", seed)

        # Seed effettivo per generare
        effective_seed = int(seed)

        # Custom intro index valido solo in modalità index
        idx = None
        if (custom_intro_mode == "index") and (custom_intro_index is not None) and (int(custom_intro_index) >= 0):
            idx = int(custom_intro_index)

        prompt, system_prompt = build_prompt_from_world(
            w,
            seed=effective_seed,
            custom_intro_mode=custom_intro_mode,
            custom_intro_index=idx,
        )

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

        return (prompt, system_prompt, next_seed)
