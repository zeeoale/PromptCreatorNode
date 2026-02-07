from pathlib import Path

def package_root() -> Path:
    return Path(__file__).resolve().parents[1]

def data_dir() -> Path:
    return package_root() / "data"

def worlds_dir() -> Path:
    return data_dir() / "worlds"
