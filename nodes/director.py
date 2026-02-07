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
            },
            "optional": {
                "custom_intro_index": ("INT", {"default": -1, "min": -1, "max": 6}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "system_prompt")
    FUNCTION = "run"
    CATEGORY = "PFN/Director"

    def run(self, world: str, seed: int, custom_intro_index: int = -1):
        w = WorldRegistry.get(world)
        if not w:
            return ("(world not found)", "")

        idx = None if custom_intro_index < 0 else int(custom_intro_index)
        prompt, system_prompt = build_prompt_from_world(w, seed=seed, custom_intro_index=idx)
        return (prompt, system_prompt)
