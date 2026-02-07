import os

def is_debug() -> bool:
    return os.environ.get("PFN_DEBUG", "0") == "1"

def log(msg: str) -> None:
    if is_debug():
        print(msg)
