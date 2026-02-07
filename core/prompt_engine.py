from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple


def _pick(arr: Any, fallback: str = "") -> str:
    if isinstance(arr, list) and arr:
        return str(random.choice(arr))
    return fallback


def _join_nonempty(parts: List[str]) -> str:
    return ", ".join([p.strip() for p in parts if p and p.strip()])


def _select_custom_intro(
    world: Dict[str, Any],
    mode: str = "auto",
    index: Optional[int] = None,
) -> str:
    ci = world.get("CUSTOM_INTRO")
    if not isinstance(ci, dict) or not ci:
        return ""

    # Normalizza keys/values in stringhe
    keys = list(ci.keys())
    values = [str(ci[k]) for k in keys if ci.get(k) is not None]

    if not values:
        return ""

    mode = (mode or "auto").lower().strip()

    if mode == "index":
        if index is None:
            return ""
        k = str(index)
        return str(ci.get(k, "")) if k in ci else ""

    if mode == "random":
        return str(random.choice(values))

    # auto: prova 0..6, altrimenti random
    for k in ["0", "1", "2", "3", "4", "5", "6"]:
        if k in ci:
            return str(ci[k])
    return str(random.choice(values))


def build_prompt_from_world(
    world: Dict[str, Any],
    seed: Optional[int] = None,
    custom_intro_mode: str = "auto",
    custom_intro_index: Optional[int] = None,
) -> Tuple[str, str]:
    if seed is not None:
        random.seed(seed)

    system_prompt = str(world.get("SYSTEM_PROMPT", "")).strip()

    custom_intro = _select_custom_intro(
        world,
        mode=custom_intro_mode,
        index=custom_intro_index,
    )

    outfits = _pick(world.get("OUTFITS"), "simple dark outfit")
    lighting = _pick(world.get("LIGHTING"), "low ambient light")
    backgrounds = _pick(world.get("BACKGROUNDS"), "intimate interior")
    objects = _pick(world.get("OBJECTS"), "personal items")
    poses = _pick(world.get("POSES"), "relaxed pose")
    expressions = _pick(world.get("EXPRESSIONS"), "calm expression")
    camera = _pick(world.get("CAMERA_ANGLES"), "eye-level framing")
    atmos = _pick(world.get("ATMOSPHERES"), "quiet cinematic mood")
    accessories = _pick(world.get("ACCESSORIES"), "")

    prompt = _join_nonempty([
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

    return (prompt.strip(), system_prompt)
