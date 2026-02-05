import os
import json
import random
import hashlib

# nuovi campi
FIELDS_ORDER = [
    "age",
    "face_type",
    "eyes",
    "eyes_color",
    "nose",
    "mouth",
    "hair",
    "hair_color",
    "skin",
    "body_type",
    "expression_base",
    "ethnicity",
]

SPECIAL_RANDOM = "(random)"
SPECIAL_EMPTY = "(empty)"
SPECIAL_NONE = "(none)"   # per ethnicity o altri campi
SPECIAL_PRESET = "(preset)"  # opzionale: scegli da preset quando disponibile

def _load_json(path: str) -> dict:
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def _get_traits_and_presets(data: dict):
    """
    Supporta due formati:
    - Nuovo: {"TRAITS": {...}, "PRESETS": {...}}
    - Legacy: {"IdentityName": {...}, "IdentityName2": {...}}
    """
    traits = data.get("TRAITS")
    presets = data.get("PRESETS") if isinstance(data.get("PRESETS"), dict) else {}

    if isinstance(traits, dict):
        # Normalizza: assicura che ogni trait sia una lista di stringhe
        norm = {}
        for k in FIELDS_ORDER:
            vals = traits.get(k, [])
            if isinstance(vals, list):
                norm[k] = [str(v).strip() for v in vals if str(v).strip()]
            else:
                norm[k] = []
        return norm, presets, True  # True = nuovo formato

    # Legacy: colleziona valori da identità singole (come fai già ora)
    identities = data
    values = {k: set() for k in FIELDS_ORDER}
    for _, obj in identities.items():
        if not isinstance(obj, dict):
            continue
        for k in FIELDS_ORDER:
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
            # opzionale: aggiungiamo (preset) solo se esistono preset e siamo nel nuovo formato
            specials = [SPECIAL_RANDOM]
            if is_new and presets:
                specials.append(SPECIAL_PRESET)
            specials += [SPECIAL_EMPTY]

            # ethnicity: aggiungi (none) sempre
            if k == "ethnicity":
                specials.insert(1, SPECIAL_NONE)  # dopo (random)
                # e se nel JSON c'è "None", lo tratto come voce normale; ma (none) è più comodo

            opts[k] = specials + (base if base else ["(no_values)"])

        preset_list = ["(none)"] + sorted(list(presets.keys())) if (is_new and presets) else ["(none)"]

        return {
            "required": {
                # preset è utile ma non obbligatorio: non cambia i dropdown, serve solo a dare un “bacino” quando scegli (preset)
                "preset": (preset_list,),
                "age": (opts["age"],),
                "face_type": (opts["face_type"],),
                "eyes": (opts["eyes"],),
                "eyes_color": (opts["eyes_color"],),
                "nose": (opts["nose"],),
                "mouth": (opts["mouth"],),
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

    def mix(self, preset, age, face_type, eyes, eyes_color, nose, mouth, hair, hair_color, skin, body_type, expression_base, ethnicity,
            random_seed, custom_intro_prefix, identities_file=None):


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
                # pesca dal preset se presente, altrimenti fallback su traits
                pool = selected_preset.get(field, [])
                if isinstance(pool, list) and pool:
                    return rng.choice(pool)
                pool = traits.get(field, [])
                return rng.choice(pool) if pool else ""
            if sel == SPECIAL_RANDOM:
                pool = traits.get(field, [])
                return rng.choice(pool) if pool else ""
            if sel == "(no_values)":
                return ""
            return sel

        for field, sel in [
            ("age", age),
            ("face_type", face_type),
            ("eyes", eyes),
            ("eyes_color", eyes_color),
            ("nose", nose),
            ("mouth", mouth),
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
