import json
from pathlib import Path
from typing import Any, Dict

def load_world_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"World file not found: {path}")

    if path.suffix.lower() != ".json":
        raise ValueError(f"World file is not a .json: {path}")

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError(f"World JSON must be an object/dict: {path}")

    return data


def load_all_worlds_from_dir(dir_path: Path) -> Dict[str, Dict[str, Any]]:
    worlds: Dict[str, Dict[str, Any]] = {}
    if not dir_path.exists():
        return worlds

    for p in sorted(dir_path.glob("*.json")):
        try:
            world = load_world_file(p)
            key = world.get("WORLD_NAME") or p.stem
            worlds[str(key)] = world
        except Exception:
            # Qui volutamente silenzioso: il registry/log deciderà se stampare errori
            continue

    return worlds
