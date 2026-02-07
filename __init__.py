# =========================
# Prompt Creator Node Suite
# DirectorNode (0.1-dev)
# =========================

from .manifest import MANIFEST
from .nodes.director import DirectorNode  # v2 only

NODE_CLASS_MAPPINGS = {
    "DirectorNode": DirectorNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DirectorNode": "Director (0.1-dev)"
}

print(f"[PFN] v{'.'.join(map(str, MANIFEST['version']))} loaded (DirectorNode only, v2)")


# --- ComfyUI mappings ---
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if DirectorNode is not None:
    NODE_CLASS_MAPPINGS["DirectorNode"] = DirectorNode
    NODE_DISPLAY_NAME_MAPPINGS["DirectorNode"] = "Director (0.1-dev)"
else:
    print(f"[PFN] DirectorNode failed to load: {_import_error}")

print(f"[PFN] v{'.'.join(map(str, MANIFEST['version']))} loaded (DirectorNode only)")
