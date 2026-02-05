import os, json

BASE = os.path.dirname(__file__)
JSON_DIR = os.path.join(BASE, "JSON_DATA")
OUT_DIR = os.path.join(BASE, "web", "extensions", "PromptCreatorNode")
OUT_PATH = os.path.join(OUT_DIR, "world_options.json")

KEYS = [
    "COLOR_REALM",
    "EPOCHS",
    "OUTFITS",
    "LIGHTING",
    "BACKGROUNDS",
    "OBJECTS",
    "POSES",
    "EXPRESSIONS",
    "CAMERA_ANGLES",
    "ATMOSPHERES",
    "ACCESSORIES"
]

def normalize_list(x):
    if not isinstance(x, list):
        return []
    out = []
    for v in x:
        if isinstance(v, str):
            v = v.strip()
            if v:
                out.append(v)
    return out

def normalize_key(data, key):
    """
    Supports:
    - list
    - dict by COLOR_REALM -> list
    Returns dict:
      {
        "__all__": [... union ...],
        "by_realm": { "realm": [...] }
      }
    """
    v = data.get(key)
    res = {"__all__": [], "by_realm": {}}

    if isinstance(v, list):
        res["__all__"] = sorted(set(normalize_list(v)))
        return res

    if isinstance(v, dict):
        all_vals = []
        by_realm = {}
        for realm, lst in v.items():
            r = str(realm).strip()
            vals = normalize_list(lst)
            if r:
                by_realm[r] = sorted(set(vals))
                all_vals.extend(vals)
        res["by_realm"] = by_realm
        res["__all__"] = sorted(set(all_vals))
        return res

    return res

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    worlds = {}

    for fn in sorted(os.listdir(JSON_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(JSON_DIR, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        w = {}
        # COLOR_REALM is always list in your worlds, but we normalize anyway
        cr = data.get("COLOR_REALM")
        w["COLOR_REALM"] = sorted(set(normalize_list(cr)))

        for k in KEYS:
            if k == "COLOR_REALM":
                continue
            w[k] = normalize_key(data, k)

        worlds[fn] = w

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(worlds, f, ensure_ascii=False, indent=2)

    print("Wrote:", OUT_PATH)
    print("Worlds:", len(worlds))

if __name__ == "__main__":
    main()
