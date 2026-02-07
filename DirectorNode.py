# DirectorNode.py
# PromptCreatorNode - DirectorNode (0.1-dev)

class DirectorNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "framing": (["extreme_closeup", "closeup", "portrait", "half_body", "full_body"], {"default": "portrait"}),
                "camera_mode": (["random", "manual", "lock"], {"default": "random"}),
                "camera_index": ("INT", {"default": 0, "min": 0, "max": 200, "step": 1}),
                "show_director_preview": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "director_preview")
    FUNCTION = "direct"
    CATEGORY = "PromptCreatorNode/Director"

    # A small default camera library (node-owned, not world-owned)
    DEFAULT_CAMERA_ANGLES = [
        "eye-level portrait, 85mm look",
        "three-quarter view, 50mm look",
        "slight low angle, 35mm look",
        "profile close-up, 105mm look",
        "top-down framing, 24mm look",
        "centered frontal composition, 70mm look",
    ]

    def direct(self, prompt, framing, camera_mode, camera_index, show_director_preview):
        cams = list(self.DEFAULT_CAMERA_ANGLES)

        # pick camera
        chosen = ""
        if camera_mode == "manual":
            if cams:
                i = max(0, min(int(camera_index), len(cams) - 1))
                chosen = cams[i]
        elif camera_mode == "lock":
            # 0.1-dev: lock behaves like manual (true persistence later)
            if cams:
                i = max(0, min(int(camera_index), len(cams) - 1))
                chosen = cams[i]
        else:  # random
            import random
            chosen = random.choice(cams) if cams else ""

        # apply framing + camera to prompt
        out_prompt = prompt.strip()
        if framing:
            out_prompt = (out_prompt + ", " if out_prompt else "") + framing.replace("_", " ")
        if chosen:
            out_prompt = out_prompt + ", " + chosen

        # preview
        preview = ""
        if show_director_preview:
            lines = [f"FRAMING: {framing}"]
            lines.append(f"CAMERA_MODE: {camera_mode}")
            if chosen:
                lines.append(f"CHOSEN_CAMERA: {chosen}")
            lines.append("CAMERA_LIBRARY:")
            for idx, c in enumerate(cams):
                marker = "->" if c == chosen else "  "
                lines.append(f"{marker} {idx}: {c}")
            preview = "\n".join(lines)

        return (out_prompt, preview)


NODE_CLASS_MAPPINGS = {
    "DirectorNode": DirectorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DirectorNode": "Director Node (0.1-dev)",
}
