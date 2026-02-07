from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..utils.paths import worlds_dir
from ..utils.logger import log
from .world_loader import load_all_worlds_from_dir


@dataclass(frozen=True)
class WorldInfo:
    name: str
    data: Dict[str, Any]


class WorldRegistry:
    _cache: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def reload(cls) -> None:
        cls._cache = load_all_worlds_from_dir(worlds_dir())
        log(f"[PFN] Loaded worlds: {len(cls._cache)} from {worlds_dir()}")

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._cache is None:
            cls.reload()

    @classmethod
    def list_names(cls) -> List[str]:
        cls._ensure_loaded()
        return sorted(cls._cache.keys()) if cls._cache else []

    @classmethod
    def get(cls, name: str) -> Optional[Dict[str, Any]]:
        cls._ensure_loaded()
        if not cls._cache:
            return None
        return cls._cache.get(name)
