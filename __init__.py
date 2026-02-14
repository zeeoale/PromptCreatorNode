# =========================
# Prompt Creator Node Suite
# =========================

MANIFEST = {
    "name": "Prompt Creator Node",
    "version": (1, 12, 0),
    "author": "TK-traumakom",
    "project": "https://github.com/zeeoale/PromptCreatorNode",
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
def _print_promptcreator_banner():
    banner = r"""
   ██████  ██████   ██████  ███    ███ ██████  ████████      
   ██   ██ ██   ██ ██    ██ ████  ████ ██   ██    ██         
   ██████  ██████  ██    ██ ██ ████ ██ ██████     ██         
   ██      ██   ██ ██    ██ ██  ██  ██ ██         ██         
   ██      ██   ██  ██████  ██      ██ ██         ██         
                                                          
 ██████ ██████  ███████  █████  ████████  ██████  ██████  
██      ██   ██ ██      ██   ██    ██    ██    ██ ██   ██ 
██      ██████  █████   ███████    ██    ██    ██ ██████  
██      ██   ██ ██      ██   ██    ██    ██    ██ ██   ██ 
 ██████ ██   ██ ███████ ██   ██    ██     ██████  ██   ██ 
                                                          
          ███    ██  ██████  ██████  ███████                        
          ████   ██ ██    ██ ██   ██ ██                             
          ██ ██  ██ ██    ██ ██   ██ █████                          
          ██  ██ ██ ██    ██ ██   ██ ██                             
          ██   ████  ██████  ██████  ███████  
 -----------------------------------------------------
                        1.12.0                         
 -----------------------------------------------------

===========================================================
PromptCreatorNode v1.12.0
A modular cinematic prompt generator for ComfyUI

Loaded nodes:
  - Prompt Generator
  - Identity Mixer (Parts)
  - Prompt Replay
  - Prompt Builder
  - Promt Tags Extractor Node (create tags for galley uploader)

Author: traumakom
===========================================================
"""
    print(banner)

_print_promptcreator_banner()

# -------------------------
# Node imports
# -------------------------

from .PromptCreatorNode import PromptCreatorNode
from .IdentityMixerNode import IdentityMixerNode
from .PromptReplayNode import PromptReplayNode
from .PromptBuilderNode import PromptBuilderNode
from .PromptTagsExtractorNode import PromptTagsExtractorNode

# -------------------------
# ComfyUI mappings
# -------------------------

NODE_CLASS_MAPPINGS = {
    "PromptCreatorNode": PromptCreatorNode,
    "IdentityMixerNode": IdentityMixerNode,
    "PromptReplayNode": PromptReplayNode,
    "PromptBuilderNode": PromptBuilderNode,
    "PromptTagsExtractorNode": PromptTagsExtractorNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptCreatorNode": "Prompt Generator",
    "IdentityMixerNode": "Identity Mixer (Parts)",
    "PromptReplayNode": "Prompt Replay",
    "PromptBuilderNode": "Prompt Builder",
    "PFN_PromptTagsExtractor": "PFN Prompt → Tags (Extractor)"

}
