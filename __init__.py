# =========================
# Prompt Creator Node Suite
# =========================

MANIFEST = {
    "name": "Prompt Creator Node",
    "version": (1, 4, 0),
    "author": "traumakom",
    "project": "https://github.com/traumakom/PromptCreatorNode",
    "description": (
        "Dynamic prompt generator for ComfyUI using modular JSON worlds, "
        "COLOR_REALM control, LoRA triggers, optional AI enhancement, "
        "and a modular Identity Mixer for consistent character generation."
    ),
}

# Log version on load (very useful for debugging)
print(
    f"[PromptCreatorNode] "
    f"v{'.'.join(map(str, MANIFEST['version']))} loaded"
)

# -------------------------
# Node imports
# -------------------------

from .PromptCreatorNode import PromptCreatorNode
from .IdentityMixerNode import IdentityMixerNode


# -------------------------
# ComfyUI mappings
# -------------------------

NODE_CLASS_MAPPINGS = {
    "PromptCreatorNode": PromptCreatorNode,
    "IdentityMixerNode": IdentityMixerNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptCreatorNode": "Prompt Generator",
    "IdentityMixerNode": "Identity Mixer (Parts)",
}
