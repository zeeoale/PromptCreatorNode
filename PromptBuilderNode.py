import os
import random
import json
import requests
from datetime import datetime


class PromptBuilderNode:
    """
    Stand-alone alternative to PromptCreatorNode:
    - Manual per-category selection (none/random/specific)
    - Keeps same enhancer stack + logging style
    """

    CATEGORY_KEYS = [
        "EPOCHS",
        "OUTFITS",
        "LIGHTING",
        "BACKGROUNDS",
        "POSES",
        "EXPRESSIONS",
        "CAMERA_ANGLES",
        "ATMOSPHERES",
    ]

    MULTI_KEYS = ["OBJECTS", "ACCESSORIES"]

    @classmethod
    def _json_dir(cls):
        return os.path.join(os.path.dirname(__file__), "JSON_DATA")

    @classmethod
    def _list_json_files(cls):
        json_dir = cls._json_dir()
        if not os.path.isdir(json_dir):
            return []
        return sorted([f for f in os.listdir(json_dir) if f.endswith(".json")])

    @classmethod
    def _load_all_world_values_union(cls):
        """
        Build dropdown option pools as union across all worlds.
        Supports:
        - list values
        - dict values by COLOR_REALM
        """
        pools = {k: set() for k in (cls.CATEGORY_KEYS + cls.MULTI_KEYS + ["COLOR_REALM"])}
        json_dir = cls._json_dir()
        for jf in cls._list_json_files():
            p = os.path.join(json_dir, jf)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            # color realms
            cr = data.get("COLOR_REALM")
            if isinstance(cr, list):
                for x in cr:
                    if isinstance(x, str) and x.strip():
                        pools["COLOR_REALM"].add(x.strip())

            # normal keys
            for k in cls.CATEGORY_KEYS + cls.MULTI_KEYS:
                v = data.get(k)
                if isinstance(v, list):
                    for x in v:
                        if isinstance(x, str) and x.strip():
                            pools[k].add(x.strip())
                elif isinstance(v, dict):
                    # values-by-realm
                    for realm, lst in v.items():
                        if isinstance(realm, str) and realm.strip():
                            pools["COLOR_REALM"].add(realm.strip())
                        if isinstance(lst, list):
                            for x in lst:
                                if isinstance(x, str) and x.strip():
                                    pools[k].add(x.strip())

        # convert to sorted lists
        out = {}
        for k, s in pools.items():
            out[k] = sorted(s)
        return out

    @classmethod
    def INPUT_TYPES(cls):
        json_files = cls._list_json_files()

        # system prompts from external file (same as PromptCreatorNode)
        system_prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.json")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_prompts = json.load(f)
            enhancer_modes = list(system_prompts.keys())
        else:
            enhancer_modes = ["standard"]

        # identities from external file (same as PromptCreatorNode)
        identities_path = os.path.join(os.path.dirname(__file__), "identities.json")
        if os.path.exists(identities_path):
            try:
                with open(identities_path, "r", encoding="utf-8") as f:
                    identities = json.load(f)
                identity_profiles = ["none"] + list(identities.keys())
            except Exception:
                identity_profiles = ["none"]
        else:
            identity_profiles = ["none"]

        pools = cls._load_all_world_values_union()

        # Helper to build dropdown: none/random + union values
        def dd(values):
            return (["none", "random"] + values,)

        # For OBJECTS / ACCESSORIES: mode + pick
        multi_pick_values = sorted(set(pools.get("OBJECTS", []) + pools.get("ACCESSORIES", [])))

        # COLOR_REALM manual select (optional)
        color_realms = pools.get("COLOR_REALM", [])
        color_realm_dd = (["none", "auto", "random"] + color_realms,)

        return {
            "required": {
                "json_name": (json_files,),

                # === Manual world direction ===
                "color_realm": color_realm_dd,

                "epochs_pick": dd(pools.get("EPOCHS", [])),
                "outfits_pick": dd(pools.get("OUTFITS", [])),
                "lighting_pick": dd(pools.get("LIGHTING", [])),
                "backgrounds_pick": dd(pools.get("BACKGROUNDS", [])),
                "poses_pick": dd(pools.get("POSES", [])),
                "expressions_pick": dd(pools.get("EXPRESSIONS", [])),
                "camera_angles_pick": dd(pools.get("CAMERA_ANGLES", [])),
                "atmospheres_pick": dd(pools.get("ATMOSPHERES", [])),

                "objects_mode": (["none", "random", "pick"],),
                "objects_pick": (["none"] + multi_pick_values,),

                "accessories_mode": (["none", "random", "pick"],),
                "accessories_pick": (["none"] + multi_pick_values,),

                # === Keep your original core controls ===
                "use_enhancer": (["none", "ollama", "llamacpp", "openai", "cohere", "gemini"],),
                "enhancer_mode": (enhancer_modes,),
                "add_symbols": (["no", "yes"],),
                "seed": ("INT", {"default": 0}),
                "gender": (["neutral", "female", "2 female", "3 female", "female vampire", "anime woman", "male", "custom"],),
                "identity_profile": (identity_profiles,),
                "lock_identity": (["no", "yes"], {"default": "yes"}),
                "custom_intro": ("STRING", {"default": "", "multiline": True}),
                "horror_intensity": (["auto"] + [str(i) for i in range(11)],),
                "sensuality_level": (["auto", "0", "1", "2", "3"],),
                "lora_triggers": ("STRING", {"default": ""}),
                "subject_count": (["1", "2", "3"],),
                "lock_last_prompt": (["no", "yes"], {"default": "no"}),
                "multi_object_count": ("INT", {"default": 1, "min": 1, "max": 5}),

                # Ollama settings
                "ollama_host": ("STRING", {"default": "http://192.168.1.1:11434"}),
                "ollama_model": ("STRING", {"default": "llama3.2"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate_prompt"
    CATEGORY = "Prompt Creator"

    # ===== shared helpers (kept compatible with PromptCreatorNode behavior) =====

    def _system_prompts(self):
        system_prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.json")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return {
                "standard": (
                    "You are a professional prompt enhancer for AI image generation. "
                    "Return ONE long, multi-clause sentence (~120–160 words), richly descriptive. "
                    "Cover: genre/style; era; foreground/midground/background; materials & textures; color palette (3–5 tones); "
                    "lighting (type/direction/intensity); atmosphere; camera angle & lens (mm); composition rule; 3–5 post-process keywords. "
                    "No story, no dialogue, no lists, no headings."
                )
            }

    def _read_api_keys(self, base_path):
        keys_path = os.path.join(base_path, "api_keys.txt")
        keys = {}
        if os.path.exists(keys_path):
            with open(keys_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        keys[k.strip()] = v.strip()
        return keys

    def _identity_profiles(self):
        identities_path = os.path.join(os.path.dirname(__file__), "identities.json")
        if os.path.exists(identities_path):
            try:
                with open(identities_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {}

    def _identity_to_text(self, identity_obj):
        if not isinstance(identity_obj, dict):
            return ""
        order = ["age", "face_type", "eyes", "nose", "mouth", "hair", "skin", "expression_base"]
        chunks = []
        for k in order:
            v = identity_obj.get(k) or identity_obj.get(k.upper())
            if isinstance(v, str) and v.strip():
                chunks.append(v.strip())
        return ", ".join(chunks)

    # ===== enhancer backends (same behavior as PromptCreatorNode) =====

    def _enhance_with_ollama(self, host, model, system_prompt, user_prompt):
        r = requests.post(f"{host}/api/chat", json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    def _enhance_with_openai(self, base_path, system_prompt, user_prompt):
        import openai
        keys = self._read_api_keys(base_path)
        openai.api_key = keys.get("openai", "")
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return resp.choices[0].message.content.strip()

    def _enhance_with_llamacpp(self, host, system_prompt, user_prompt, temperature=0.7, top_p=0.9, n_predict=220):
        host = host.rstrip("/")

        # Try OpenAI compatible endpoint
        try:
            r = requests.post(
                f"{host}/v1/chat/completions",
                json={
                    "model": "llama",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": float(temperature),
                    "top_p": float(top_p),
                    "max_tokens": int(n_predict),
                    "stream": False,
                },
                timeout=120,
            )

            if r.status_code == 200:
                j = r.json()
                content = (
                    j.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                content = (content or "").strip()
                if content:
                    return content
        except Exception:
            pass

        # Fallback
        r = requests.post(
            f"{host}/completion",
            json={
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "temperature": float(temperature),
                "top_p": float(top_p),
                "n_predict": int(n_predict),
                "stream": False,
            },
            timeout=120,
        )
        r.raise_for_status()
        j = r.json()
        content = (j.get("content") or j.get("completion") or "").strip()
        if not content:
            raise RuntimeError(f"llama.cpp returned no content. Keys: {list(j.keys())}")
        return content

    def _enhance_with_cohere(self, base_path, system_prompt, user_prompt):
        import re
        try:
            import cohere
        except ImportError:
            print("[PromptBuilder] Cohere SDK not installed, skipping enhance.")
            return user_prompt

        keys = self._read_api_keys(base_path)
        api_key = keys.get("cohere", "").strip()
        if not api_key:
            print("[PromptBuilder] No Cohere API key found, skipping enhance.")
            return user_prompt

        try:
            co = cohere.ClientV2(api_key=api_key)
        except Exception as e:
            print(f"[PromptBuilder] Cohere ClientV2 not available: {e}")
            return user_prompt

        user_msg = (
            f"Seed: {user_prompt}\n\n"
            "Return exactly one long sentence (around 100 to 150 words), no line breaks."
        )

        try:
            resp = co.chat(
                model="command-r-08-2024",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=700,
                temperature=0.9,
            )

            content = ""
            if hasattr(resp, "message") and getattr(resp.message, "content", None):
                parts = resp.message.content
                texts = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
                content = " ".join(texts).strip()

            if not content:
                print("[PromptBuilder] Cohere returned empty content.")
                return user_prompt

            content = re.sub(r"\s*\n+\s*", " ", content).strip()
            return content

        except Exception as e:
            print(f"[PromptBuilder] Error calling Cohere chat: {e}")
            return user_prompt

    def _enhance_with_gemini(self, base_path, system_prompt, user_prompt):
        import google.generativeai as genai
        keys = self._read_api_keys(base_path)
        genai.configure(api_key=keys.get("gemini", ""))
        model = genai.GenerativeModel("models/gemini-2.5-pro")
        txt = (
            f"SYSTEM: {system_prompt}\n"
            f"USER: {user_prompt}\n"
            "Return only the final prompt as a single paragraph."
        )
        r = model.generate_content(txt)
        return r.candidates[0].content.parts[0].text.strip()

    # ===== logging =====

    @staticmethod
    def log_prompt_run(
        json_name,
        enhancer_mode,
        gender,
        custom_intro,
        lora_triggers,
        final_prompt,
        source="generated",
        node_version="1.0.0",
    ):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "prompt_history.jsonl")

        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "json_world": json_name,
            "system_prompt": enhancer_mode,
            "gender": gender,
            "custom_intro": custom_intro.strip() if (gender == "custom" and isinstance(custom_intro, str) and custom_intro.strip()) else None,
            "lora_triggers": lora_triggers,
            "final_prompt": final_prompt,
            "source": source,
            "node_version": node_version
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ===== builder logic =====

    def _pick_from_world(self, data, key, color_realm_value, mode, specific_value, multi_count=1):
        """
        mode: "none" / "random" / "pick"
        For single keys, 'pick' just means use specific_value.
        For multi keys, if mode random: sample multi_count; if pick: use specific_value (single).
        Supports COLOR_REALM dict-based lists if available.
        """
        if mode == "none":
            return []

        # collect candidate list from world
        candidates = []
        v = data.get(key)

        if color_realm_value and isinstance(v, dict):
            realm_list = v.get(color_realm_value, [])
            if isinstance(realm_list, list):
                candidates = [x.strip() for x in realm_list if isinstance(x, str) and x.strip()]
        elif isinstance(v, list):
            candidates = [x.strip() for x in v if isinstance(x, str) and x.strip()]
        elif isinstance(v, dict):
            # if dict-by-realm but realm not selected, merge all
            for _, lst in v.items():
                if isinstance(lst, list):
                    candidates.extend([x.strip() for x in lst if isinstance(x, str) and x.strip()])

        # "pick" uses specific_value even if not in candidates (manual override)
        if mode == "pick":
            if specific_value and str(specific_value).lower() != "none":
                return [str(specific_value).strip()]
            return []

        # random
        if not candidates:
            return []
        if key in self.MULTI_KEYS:
            return random.sample(candidates, min(int(multi_count), len(candidates)))
        return [random.choice(candidates)]

    def generate_prompt(
        self,
        json_name,
        color_realm,

        epochs_pick,
        outfits_pick,
        lighting_pick,
        backgrounds_pick,
        poses_pick,
        expressions_pick,
        camera_angles_pick,
        atmospheres_pick,

        objects_mode,
        objects_pick,
        accessories_mode,
        accessories_pick,

        use_enhancer,
        enhancer_mode,
        add_symbols,
        seed,
        gender,
        identity_profile,
        lock_identity,
        custom_intro,
        horror_intensity,
        sensuality_level,
        lora_triggers,
        subject_count,
        lock_last_prompt,
        multi_object_count,
        ollama_host,
        ollama_model,
    ):
        base_path = os.path.dirname(__file__)
        json_path = os.path.join(base_path, "JSON_DATA", json_name)

        # history lock (same behavior)
        history_path = os.path.join(base_path, "history", f"last_prompt_{json_name}.txt")
        if lock_last_prompt == "yes" and os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                prompt = f.read().strip()
            self.log_prompt_run(
                json_name=json_name,
                enhancer_mode=enhancer_mode,
                gender=gender,
                custom_intro=custom_intro,
                lora_triggers=lora_triggers,
                final_prompt=prompt,
                source="history_lock",
                node_version="1.0.0"
            )
            print("[PromptBuilder] Prompt locked and loaded from history")
            return (prompt,)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[PromptBuilder] Errore nel caricamento del JSON: {e}")
            return ("",)

        # Seed for deterministic "random" picks
        if seed:
            random.seed(seed)

        # Identity profile (prompt-only consistency)
        identity_txt = ""
        if identity_profile != "none" and lock_identity == "yes":
            identities = self._identity_profiles()
            identity_txt = self._identity_to_text(identities.get(identity_profile, {}))
            print("[PromptBuilder][DEBUG] identity_profile:", identity_profile)
            print("[PromptBuilder][DEBUG] lock_identity:", lock_identity)
            print("[PromptBuilder][DEBUG] identity_txt:", repr(identity_txt))

        parts = []

        # Gender / subject intro (same logic as PromptCreatorNode)
        if gender == "custom" and isinstance(custom_intro, str) and custom_intro.strip():
            parts.append(custom_intro.strip())
        else:
            gender_inserted = False
            if gender in data:
                values = data[gender]
                if isinstance(values, list) and values:
                    parts.append(random.choice(values))
                    gender_inserted = True
            if not gender_inserted:
                gender_defaults = {
                    "male": "a mysterious man",
                    "female": "a beautiful woman",
                    "2 female": "two beautiful womans",
                    "3 female": "three unique beautiful womans",
                    "female vampire": "a beautiful vampire woman",
                    "anime woman": "a beautiful anime woman"
                }
                parts.append(gender_defaults.get(gender, "a striking figure"))

        # COLOR_REALM selection
        color_realm_value = None
        if "COLOR_REALM" in data and isinstance(data.get("COLOR_REALM"), list) and data["COLOR_REALM"]:
            if color_realm == "auto":
                # behave like creator: random realm
                color_realm_value = random.choice(data["COLOR_REALM"])
            elif color_realm == "random":
                color_realm_value = random.choice(data["COLOR_REALM"])
            else:
                # specific realm requested
                if color_realm in data["COLOR_REALM"]:
                    color_realm_value = color_realm

            if color_realm_value:
                parts.append(color_realm_value)
                print(f"[PromptBuilder] Using COLOR_REALM: {color_realm_value}")

        # Single category picks
        mapping = {
            "EPOCHS": ("random" if epochs_pick == "random" else ("none" if epochs_pick == "none" else "pick"), epochs_pick),
            "OUTFITS": ("random" if outfits_pick == "random" else ("none" if outfits_pick == "none" else "pick"), outfits_pick),
            "LIGHTING": ("random" if lighting_pick == "random" else ("none" if lighting_pick == "none" else "pick"), lighting_pick),
            "BACKGROUNDS": ("random" if backgrounds_pick == "random" else ("none" if backgrounds_pick == "none" else "pick"), backgrounds_pick),
            "POSES": ("random" if poses_pick == "random" else ("none" if poses_pick == "none" else "pick"), poses_pick),
            "EXPRESSIONS": ("random" if expressions_pick == "random" else ("none" if expressions_pick == "none" else "pick"), expressions_pick),
            "CAMERA_ANGLES": ("random" if camera_angles_pick == "random" else ("none" if camera_angles_pick == "none" else "pick"), camera_angles_pick),
            "ATMOSPHERES": ("random" if atmospheres_pick == "random" else ("none" if atmospheres_pick == "none" else "pick"), atmospheres_pick),
        }

        # Apply in a stable order (director feel)
        order = ["EPOCHS", "OUTFITS", "LIGHTING", "BACKGROUNDS", "POSES", "EXPRESSIONS", "CAMERA_ANGLES", "ATMOSPHERES"]
        for key in order:
            mode, spec = mapping[key]
            picked = self._pick_from_world(data, key, color_realm_value, mode, spec, multi_count=1)
            parts.extend(picked)

        # Multi keys
        parts.extend(self._pick_from_world(
            data, "OBJECTS", color_realm_value,
            objects_mode,
            objects_pick if objects_mode == "pick" else "",
            multi_count=multi_object_count
        ))
        parts.extend(self._pick_from_world(
            data, "ACCESSORIES", color_realm_value,
            accessories_mode,
            accessories_pick if accessories_mode == "pick" else "",
            multi_count=multi_object_count
        ))

        # Horror intensity (same as creator)
        if horror_intensity != "auto" and "HORROR_INTENSITY" in data:
            try:
                horror_level = int(horror_intensity)
                intensity_entries = data["HORROR_INTENSITY"]
                if isinstance(intensity_entries, dict):
                    matching = intensity_entries.get(str(horror_level))
                    if matching:
                        parts.append(matching)
            except ValueError:
                pass

        # Sensuality level (same as creator)
        if sensuality_level != "auto" and "SENSUALITY_LEVEL" in data:
            try:
                s_level = int(sensuality_level)
                s_entries = data["SENSUALITY_LEVEL"]
                if isinstance(s_entries, dict):
                    matching = s_entries.get(str(s_level))
                    if matching:
                        parts.append(matching)
            except ValueError:
                pass

        if subject_count != "1":
            parts.append(f"{subject_count} subjects present")

        prompt = ", ".join([p for p in parts if isinstance(p, str) and p.strip()])

        if identity_txt:
            prompt = identity_txt + ", " + prompt
            print("[PromptBuilder][DEBUG] prompt_pre_enhancer:", prompt)

        # System prompt
        system_prompts = self._system_prompts()
        system_prompt = system_prompts.get(enhancer_mode, system_prompts["standard"])
        user_prompt = f"Enhance this prompt: {prompt}"

        # Enhancer backends
        if use_enhancer != "none":
            print("[PromptBuilder][DEBUG] use_enhancer:", use_enhancer)
            print("[PromptBuilder][DEBUG] enhancer_mode:", enhancer_mode)
            print("[PromptBuilder][DEBUG] system_prompt:", system_prompt)
            print("[PromptBuilder][DEBUG] user_prompt:", user_prompt)

            try:
                if use_enhancer == "ollama":
                    prompt = self._enhance_with_ollama(ollama_host, ollama_model, system_prompt, user_prompt)
                elif use_enhancer == "llamacpp":
                    prompt = self._enhance_with_llamacpp(ollama_host, system_prompt, user_prompt)
                elif use_enhancer == "openai":
                    prompt = self._enhance_with_openai(base_path, system_prompt, user_prompt)
                elif use_enhancer == "cohere":
                    prompt = self._enhance_with_cohere(base_path, system_prompt, user_prompt)
                elif use_enhancer == "gemini":
                    prompt = self._enhance_with_gemini(base_path, system_prompt, user_prompt)
            except Exception as e:
                print(f"[PromptBuilder] Errore nell'enhancer ({use_enhancer}): {e}")

        # LoRA triggers
        if isinstance(lora_triggers, str) and lora_triggers.strip():
            lts = [x.strip() for x in lora_triggers.split(",") if x.strip()]
            if lts:
                prompt += ", " + ", ".join(lts)
                print(f"[PromptBuilder] LoRA triggers aggiunti: {lts}")

        if add_symbols == "yes":
            prompt = f"[{prompt}]"

        os.makedirs(os.path.join(base_path, "history"), exist_ok=True)
        with open(history_path, "w", encoding="utf-8") as f:
            f.write(prompt.strip())

        print(f"[PromptBuilder] Prompt finale: {prompt}")
        self.log_prompt_run(
            json_name=json_name,
            enhancer_mode=enhancer_mode,
            gender=gender,
            custom_intro=custom_intro,
            lora_triggers=lora_triggers,
            final_prompt=prompt,
            source="generated_builder",
            node_version="1.0.0"
        )

        return (prompt,)
    # ===== ComfyUI mappings =====
NODE_CLASS_MAPPINGS = {
    "PromptBuilderNode": PromptBuilderNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptBuilderNode": "Prompt Builder"
}