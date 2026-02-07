from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple


def _pick_with_rng(rng: random.Random, arr: Any, fallback: str = "") -> str:
    if isinstance(arr, list) and arr:
        return str(rng.choice(arr))
    return fallback


def _join_nonempty(parts: List[str]) -> str:
    return ", ".join([p.strip() for p in parts if p and p.strip()])


def _seed_for(seed: int, tag: str) -> int:
    # deterministico, stabile tra run (a differenza di hash() che può variare)
    h = 0
    for ch in tag:
        h = (h * 31 + ord(ch)) & 0x7FFFFFFF
    return (seed ^ h) & 0x7FFFFFFF


def _select_custom_intro(
    rng: random.Random,
    world: Dict[str, Any],
    mode: str = "auto",
    index: Optional[int] = None,
) -> str:
    ci = world.get("CUSTOM_INTRO")
    if not isinstance(ci, dict) or not ci:
        return ""

    values = [str(v) for v in ci.values() if v is not None and str(v).strip()]
    if not values:
        return ""

    mode = (mode or "auto").lower().strip()

    if mode == "index":
        if index is None:
            return ""
        k = str(index)
        return str(ci.get(k, "")) if k in ci else ""

    if mode == "random":
        return str(rng.choice(values))

    # auto: prova 0..6, altrimenti random
    for k in ["0", "1", "2", "3", "4", "5", "6"]:
        if k in ci:
            return str(ci[k])
    return str(rng.choice(values))


def build_prompt_from_world(
    world: Dict[str, Any],
    seed: int = 0,
    custom_intro_mode: str = "auto",
    custom_intro_index: Optional[int] = None,
    lock_camera: bool = True,
    lock_lighting: bool = True,
    lock_outfit: bool = True,
    lock_pose: bool = False,
) -> Tuple[str, str, str]:

    """
    Returns: (prompt, system_prompt, director_notes)

    lock_camera:
      - True  => camera selection uses a deterministic RNG derived from seed
      - False => camera selection uses the main RNG (varies with seed changes)
    """

    # RNG principale per la maggior parte delle scelte
    base_rng = random.Random(seed)

    system_prompt = str(world.get("SYSTEM_PROMPT", "")).strip()

    custom_intro = _select_custom_intro(
        base_rng,
        world,
        mode=custom_intro_mode,
        index=custom_intro_index,
    )

    # Outfit RNG
    outfit_rng = random.Random(_seed_for(seed, "outfit")) if lock_outfit else base_rng
    outfit = _pick_with_rng(outfit_rng, world.get("OUTFITS"), "simple dark outfit")    
# Lighting RNG
    lighting_rng = random.Random(_seed_for(seed, "lighting")) if lock_lighting else base_rng
    lighting = _pick_with_rng(lighting_rng, world.get("LIGHTING"), "low ambient light")    
    background = _pick_with_rng(base_rng, world.get("BACKGROUNDS"), "intimate interior")
    objects = _pick_with_rng(base_rng, world.get("OBJECTS"), "personal items")
    # Pose RNG (default False: di solito vuoi variazione nella posa)
    pose_rng = random.Random(_seed_for(seed, "pose")) if lock_pose else base_rng
    pose = _pick_with_rng(pose_rng, world.get("POSES"), "relaxed pose")
    expression = _pick_with_rng(base_rng, world.get("EXPRESSIONS"), "calm expression")

    # Camera RNG separato (lock selettivo)
    camera_list = world.get("CAMERA_ANGLES")
    if lock_camera:
        camera_rng = random.Random(_seed_for(seed, "camera"))
    else:
        camera_rng = base_rng
    camera = _pick_with_rng(camera_rng, camera_list, "eye-level framing")

    atmosphere = _pick_with_rng(base_rng, world.get("ATMOSPHERES"), "quiet cinematic mood")
    accessory = _pick_with_rng(base_rng, world.get("ACCESSORIES"), "")

    prompt = _join_nonempty([
        custom_intro,
        outfit,
        lighting,
        background,
        objects,
        pose,
        expression,
        camera,
        atmosphere,
        accessory,
    ])

    selections = {
        "custom_intro": custom_intro,
        "lock_outfit": str(lock_outfit).lower(),
        "outfit": outfit,
        "lock_lighting": str(lock_lighting).lower(),
        "lighting": lighting,
        "background": background,
        "objects": objects,
        "lock_pose": str(lock_pose).lower(),
        "pose": pose,
        "expression": expression,
        "camera": camera,
        "atmosphere": atmosphere,
        "accessory": accessory,
        "lock_camera": str(lock_camera).lower(),
    }

    director_notes = "\n".join(
        [f"{k}: {v}" for k, v in selections.items() if v and str(v).strip()]
    ).strip()

    return (prompt.strip(), system_prompt, director_notes)
