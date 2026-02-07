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
    overrides: Optional[Dict[str, str]] = None,
) -> Tuple[str, str, str, Dict[str, str]]:
    """
    Returns: (prompt, system_prompt, director_notes, chosen)

    overrides: if provided, keys like "camera","outfit","lighting","pose","expression","background","objects","atmosphere","accessory"
              will be used instead of sampling.
    """

    overrides = overrides or {}

    base_rng = random.Random(seed)
    system_prompt = str(world.get("SYSTEM_PROMPT", "")).strip()

    custom_intro = overrides.get("custom_intro") or _select_custom_intro(
        base_rng, world, mode=custom_intro_mode, index=custom_intro_index
    )

    outfit_rng = random.Random(_seed_for(seed, "outfit")) if lock_outfit else base_rng
    outfit = overrides.get("outfit") or _pick_with_rng(outfit_rng, world.get("OUTFITS"), "simple dark outfit")

    lighting_rng = random.Random(_seed_for(seed, "lighting")) if lock_lighting else base_rng
    lighting = overrides.get("lighting") or _pick_with_rng(lighting_rng, world.get("LIGHTING"), "low ambient light")

    background = overrides.get("background") or _pick_with_rng(base_rng, world.get("BACKGROUNDS"), "intimate interior")
    objects = overrides.get("objects") or _pick_with_rng(base_rng, world.get("OBJECTS"), "personal items")

    pose_rng = random.Random(_seed_for(seed, "pose")) if lock_pose else base_rng
    pose = overrides.get("pose") or _pick_with_rng(pose_rng, world.get("POSES"), "relaxed pose")

    expression = overrides.get("expression") or _pick_with_rng(base_rng, world.get("EXPRESSIONS"), "calm expression")

    camera_rng = random.Random(_seed_for(seed, "camera")) if lock_camera else base_rng
    camera = overrides.get("camera") or _pick_with_rng(camera_rng, world.get("CAMERA_ANGLES"), "eye-level framing")

    atmosphere = overrides.get("atmosphere") or _pick_with_rng(base_rng, world.get("ATMOSPHERES"), "quiet cinematic mood")
    accessory = overrides.get("accessory") or _pick_with_rng(base_rng, world.get("ACCESSORIES"), "")

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

    chosen: Dict[str, str] = {
        "custom_intro": custom_intro,
        "outfit": outfit,
        "lighting": lighting,
        "background": background,
        "objects": objects,
        "pose": pose,
        "expression": expression,
        "camera": camera,
        "atmosphere": atmosphere,
        "accessory": accessory,
    }

    notes_lines = [
        f"outfit: {outfit}",
        f"lighting: {lighting}",
        f"background: {background}",
        f"objects: {objects}",
        f"pose: {pose}",
        f"expression: {expression}",
        f"camera: {camera}",
        f"atmosphere: {atmosphere}",
        f"accessory: {accessory}",
        f"lock_camera: {str(lock_camera).lower()}",
        f"lock_lighting: {str(lock_lighting).lower()}",
        f"lock_outfit: {str(lock_outfit).lower()}",
        f"lock_pose: {str(lock_pose).lower()}",
        f"overrides: {', '.join(sorted(overrides.keys())) if overrides else '(none)'}",
    ]

    director_notes = "\n".join([l for l in notes_lines if l.strip()]).strip()

    return (prompt.strip(), system_prompt, director_notes, chosen)
