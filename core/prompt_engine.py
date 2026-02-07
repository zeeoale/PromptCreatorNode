from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


def _pick(arr: Any, fallback: str = "") -> str:
    if isinstance(arr, list) and arr:
        return str(random.choice(arr))
    return fallback


def _join_nonempty(parts: List[str]) -> str:
    return ", ".join([p.strip() for p in parts if p and p.strip()])


def build_prompt_from_world(
    world: Dict[str, Any],
    seed: Optional[int] = None,
    custom_intro_index: Optional[int] = None,
) -> str:
    if seed is not None:
        random.seed(seed)

    # 1) system prompt (se ti serve per debug/log o per ritorni futuri)
    system_prompt = str(world.get("SYSTEM_PROMPT", "")).strip()

    # 2) prendi un custom_intro (se c’è)
    custom_intro = ""
    ci = world.get("CUSTOM_INTRO")
    if isinstance(ci, dict) and ci:
        if custom_intro_index is not None and str(custom_intro_index) in ci:
            custom_intro = str(ci[str(custom_intro_index)])
        else:
            # prova 0..6, altrimenti random tra valori
            for k in ["0", "1", "2", "3", "4", "5", "6"]:
                if k in ci:
                    custom_intro = str(ci[k])
                    break
            if not custom_intro:
                custom_intro = str(random.choice(list(ci.values())))

    # 3) selezioni modulari (liste)
    outfits = _pick(world.get("OUTFITS"), "simple dark outfit")
    lighting = _pick(world.get("LIGHTING"), "low ambient light")
    backgrounds = _pick(world.get("BACKGROUNDS"), "intimate interior")
    objects = _pick(world.get("OBJECTS"), "personal items")
    poses = _pick(world.get("POSES"), "relaxed pose")
    expressions = _pick(world.get("EXPRESSIONS"), "calm expression")
    camera = _pick(world.get("CAMERA_ANGLES"), "eye-level framing")
    atmos = _pick(world.get("ATMOSPHERES"), "quiet cinematic mood")
    accessories = _pick(world.get("ACCESSORIES"), "")

    # 4) compone una frase unica (poi la raffiniamo nello step successivo)
    core = _join_nonempty([
        custom_intro,
        outfits,
        lighting,
        backgrounds,
        objects,
        poses,
        expressions,
        camera,
        atmos,
        accessories,
    ])

    # system_prompt lo teniamo separato: qui ritorniamo solo il prompt “artistico”
    return core.strip(), system_prompt
