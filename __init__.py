# =========================
# Prompt Creator Node Suite
# DirectorNode (0.1-dev)
# =========================

from .manifest import MANIFEST
from .nodes.director import DirectorNode  # v2 only
from .nodes.session_load import DirectorSessionLoad
from .nodes.session_merge import DirectorSessionMerge
from .nodes.session_merge_dropdown import DirectorSessionMergeDropdown




NODE_CLASS_MAPPINGS = {
    "DirectorNode": DirectorNode,
    "DirectorSessionLoad": DirectorSessionLoad,
    "DirectorSessionMerge": DirectorSessionMerge,
    "DirectorSessionMergeDropdown": DirectorSessionMergeDropdown,



}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DirectorNode": "Director (0.1-dev)",
    "DirectorSessionLoad": "Director Session Load",
    "DirectorSessionMerge": "Director Session Merge",
    "DirectorSessionMergeDropdown": "Director Session Merge (Dropdown)",



}


