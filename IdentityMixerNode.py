import os
import json
import random
import hashlib

# ✅ v1.11.0: split makeup -> eye_makeup + lip_makeup
FIELDS_ORDER = [
    "age",
    "face_type",
    "eyes",
    "eyes_color",
    "eye_makeup",      # ✅ NEW
    "nose",
    "mouth",
    "lip_makeup",      # ✅ NEW
    "hair",
    "hair_color",
    "skin",
    "body_type",
    "expression_base",
    "ethnicity",
]

SPECIAL_RANDOM = "(random)"
SPECIAL_EMPTY = "(empty)"
SPECIAL_NONE = "(none)"       # per ethnicity o altri campi
SPECIAL_PRESET = "(preset)"   # scegli da preset quando disponibile

def _load_json(path: str) -> dict:
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def _norm_list(vals):
    if isinstance(vals, list):
        return [str(v).strip() for v in vals if str(v).strip()]
    if isinstance(vals, str):
        s = vals.strip()
        return [s] if s else []
    return []

def _merge_unique(*lists):
    seen = set()
    out = []
    for lst in lists:
        for v in (lst or []):
            vv = str(v).strip()
            if vv and vv not in seen:
                seen.add(vv)
                out.append(vv)
    return out

def _get_traits_and_presets(data: dict):
    """
    Supporta due formati:
    - Nuovo: {"TRAITS": {...}, "PRESETS": {...}}
    - Legacy: {"IdentityName": {...}, "IdentityName2": {...}}

    ✅ v1.11.0: retro-compat per vecchio campo "makeup":
      - se in TRAITS esiste solo "makeup", lo usa come fallback per eye_makeup & lip_makeup
      - se nei PRESETS esiste "makeup", lo usa come fallback per eye_makeup & lip_makeup
    """
    traits_raw = data.get("TRAITS")
    presets = data.get("PRESETS") if isinstance(data.get("PRESETS"), dict) else {}

    if isinstance(traits_raw, dict):
        # Normalizza tutti i campi "nuovi"
        norm = {}
        for k in FIELDS_ORDER:
            norm[k] = _norm_list(traits_raw.get(k, []))

        # ✅ fallback: vecchio "makeup" -> eye_makeup & lip_makeup
        legacy_makeup = _norm_list(traits_raw.get("makeup", []))
        if legacy_makeup:
            if not norm.get("eye_makeup"):
                norm["eye_makeup"] = legacy_makeup[:]
            else:
                norm["eye_makeup"] = _merge_unique(norm["eye_makeup"], legacy_makeup)

            if not norm.get("lip_makeup"):
                norm["lip_makeup"] = legacy_makeup[:]
            else:
                norm["lip_makeup"] = _merge_unique(norm["lip_makeup"], legacy_makeup)

        # ✅ normalizza anche presets: se manca eye/lip ma c'è makeup, lo distribuisce
        if isinstance(presets, dict) and presets:
            fixed_presets = {}
            for pname, pobj in presets.items():
                if not isinstance(pobj, dict):
                    continue
                p = dict(pobj)

                p_makeup = _norm_list(p.get("makeup", []))
                if p_makeup:
                    if not _norm_list(p.get("eye_makeup", [])):
                        p["eye_makeup"] = p_makeup[:]
                    else:
                        p["eye_makeup"] = _merge_unique(_norm_list(p.get("eye_makeup", [])), p_makeup)

                    if not _norm_list(p.get("lip_makeup", [])):
                        p["lip_makeup"] = p_makeup[:]
                    else:
                        p["lip_makeup"] = _merge_unique(_norm_list(p.get("lip_makeup", [])), p_makeup)

                fixed_presets[pname] = p
            presets = fixed_presets

        return norm, presets, True  # True = nuovo formato

    # Legacy: colleziona valori da identità singole
    identities = data
    values = {k: set() for k in FIELDS_ORDER}

    # In legacy non esistono eye_makeup/lip_makeup: se trovi MAKEUP lo mettiamo su entrambi.
    for _, obj in identities.items():
        if not isinstance(obj, dict):
            continue

        # legge makeup legacy (sia "makeup" che "MAKEUP")
        legacy_m = obj.get("makeup") or obj.get("MAKEUP")

        for k in FIELDS_ORDER:
            if k in ("eye_makeup", "lip_makeup"):
                # fallback
                v = legacy_m
            else:
                v = obj.get(k) or obj.get(k.upper())

            if isinstance(v, str):
                v = v.strip()
                if v:
                    values[k].add(v)

    legacy_traits = {k: sorted(list(vals)) for k, vals in values.items()}
    return legacy_traits, {}, False

def _make_signature(parts: dict) -> str:
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:10]

class IdentityMixerNode:
    @classmethod
    def INPUT_TYPES(cls):
        identities_path = os.path.join(os.path.dirname(__file__), "identity.json")
        data = _load_json(identities_path)
        traits, presets, is_new = _get_traits_and_presets(data)

        opts = {}
        for k in FIELDS_ORDER:
            base = traits.get(k, [])
            specials = [SPECIAL_RANDOM]
            if is_new and presets:
                specials.append(SPECIAL_PRESET)
            specials += [SPECIAL_EMPTY]

            # ethnicity: aggiungi (none) sempre
            if k == "ethnicity":
                specials.insert(1, SPECIAL_NONE)

            opts[k] = specials + (base if base else ["(no_values)"])

        preset_list = ["(none)"] + sorted(list(presets.keys())) if (is_new and presets) else ["(none)"]

        return {
            "required": {
                "preset": (preset_list,),

                "age": (opts["age"],),
                "face_type": (opts["face_type"],),

                "eyes": (opts["eyes"],),
                "eyes_color": (opts["eyes_color"],),
                "eye_makeup": (opts["eye_makeup"],),   # ✅ NEW

                "nose": (opts["nose"],),

                "mouth": (opts["mouth"],),
                "lip_makeup": (opts["lip_makeup"],),   # ✅ NEW

                "hair": (opts["hair"],),
                "hair_color": (opts["hair_color"],),

                "skin": (opts["skin"],),
                "body_type": (opts["body_type"],),
                "expression_base": (opts["expression_base"],),
                "ethnicity": (opts["ethnicity"],),

                "random_seed": ("INT", {"default": 123456, "min": 0, "max": 2147483647}),
                "custom_intro_prefix": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "identities_file": ("STRING", {"default": identities_path}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("identity_txt", "identity_signature", "identity_meta_json")
    FUNCTION = "mix"
    CATEGORY = "PromptCreator"

    def mix(
        self,
        preset,
        age, face_type,
        eyes, eyes_color, eye_makeup,
        nose,
        mouth, lip_makeup,
        hair, hair_color,
        skin, body_type, expression_base, ethnicity,
        random_seed, custom_intro_prefix,
        identities_file=None
    ):
        data = _load_json(identities_file) if identities_file else {}
        traits, presets, is_new = _get_traits_and_presets(data)

        rng = random.Random(int(random_seed))

        chosen = {}
        selected_preset = presets.get(preset, {}) if (is_new and preset and preset != "(none)") else {}

        def pick_value(field: str, sel: str) -> str:
            if sel == SPECIAL_EMPTY:
                return ""
            if sel == SPECIAL_NONE:
                return ""
            if sel == SPECIAL_PRESET:
                pool = _norm_list(selected_preset.get(field, []))
                if pool:
                    return rng.choice(pool)
                pool = traits.get(field, [])
                return rng.choice(pool) if pool else ""
            if sel == SPECIAL_RANDOM:
                pool = traits.get(field, [])
                return rng.choice(pool) if pool else ""
            if sel == "(no_values)":
                return ""
            return sel

        # ✅ ordine coerente con FIELDS_ORDER
        for field, sel in [
            ("age", age),
            ("face_type", face_type),

            ("eyes", eyes),
            ("eyes_color", eyes_color),
            ("eye_makeup", eye_makeup),

            ("nose", nose),

            ("mouth", mouth),
            ("lip_makeup", lip_makeup),

            ("hair", hair),
            ("hair_color", hair_color),

            ("skin", skin),
            ("body_type", body_type),
            ("expression_base", expression_base),
            ("ethnicity", ethnicity),
        ]:
            chosen[field] = pick_value(field, sel)

        chunks = [chosen[k] for k in FIELDS_ORDER if isinstance(chosen.get(k), str) and chosen[k].strip()]
        identity_core = ", ".join(chunks).strip()

        fixed_tail = "masterpiece, best quality, amazing quality, 4k, very aesthetic, high resolution, ultra-detailed, absurdres, newest, scenery, depth of field, volumetric lighting"

        prefix = (custom_intro_prefix or "").strip()
        parts = []
        if prefix:
            parts.append(prefix)
        if identity_core:
            parts.append(identity_core)

        custom_intro_out = ", ".join([p.strip().strip(",") for p in parts if p.strip()])
        custom_intro_out = (custom_intro_out.rstrip(", ") + ", " + fixed_tail) if custom_intro_out else fixed_tail

        sig = _make_signature(chosen)
        meta = {
            "identity_signature": sig,
            "random_seed": int(random_seed),
            "preset": preset if preset else "(none)",
            "parts": chosen
        }
        meta_json = json.dumps(meta, ensure_ascii=False)

        return (custom_intro_out, sig, meta_json)
