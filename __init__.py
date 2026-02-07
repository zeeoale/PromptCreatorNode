from .manifest import MANIFEST

# New-structure nodes (v2)
try:
    from .nodes.director import DirectorNode
except Exception as e:
    DirectorNode = None
    print(f"[PFN] DirectorNode load failed: {e}")

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if DirectorNode is not None:
    NODE_CLASS_MAPPINGS["DirectorNode"] = DirectorNode
    NODE_DISPLAY_NAME_MAPPINGS["DirectorNode"] = "Director (0.1-dev)"
