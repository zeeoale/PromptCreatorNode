import os
import random
import json
import requests
from datetime import datetime


class PromptCreatorNode:
    NODE_VERSION = "1.11.0"

    @classmethod
    def INPUT_TYPES(cls):
        base_path = os.path.dirname(__file__)
        json_dir = os.path.join(base_path, "JSON_DATA")
        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")] if os.path.isdir(json_dir) else []

        # --- Camera Angles (optional) from camera_angles.json ---
        camera_angle_list = ["none"]
        camera_angles_path = os.path.join(base_path, "camera_angles.json")
        if os.path.exists(camera_angles_path):
            try:
                with open(camera_angles_path, "r", encoding="utf-8") as f:
                    camera_data = json.load(f)
                ids = camera_data.get("ids", [])
                if isinstance(ids, list):
                    camera_angle_list += [str(x) for x in ids if str(x).strip()]
            except Exception:
                pass

        # --- Camera Light (new) from camera_light.json ---
        camera_light_list = ["none"]
        camera_light_path = os.path.join(base_path, "camera_light.json")
        if os.path.exists(camera_light_path):
            try:
                with open(camera_light_path, "r", encoding="utf-8") as f:
                    light_data = json.load(f)
                ids = light_data.get("ids", [])
                if isinstance(ids, list):
                    camera_light_list += [str(x) for x in ids if str(x).strip()]
            except Exception:
                pass

        # --- Daytime (new) from daytime.json ---
        daytime_list = ["none"]
        daytime_path = os.path.join(base_path, "daytime.json")
        if os.path.exists(daytime_path):
            try:
                with open(daytime_path, "r", encoding="utf-8") as f:
                    dt_data = json.load(f)
                ids = dt_data.get("ids", [])
                if isinstance(ids, list):
                    daytime_list += [str(x) for x in ids if str(x).strip()]
            except Exception:
                pass

        # --- system_prompt.json (enhancer modes) ---
        system_prompt_path = os.path.join(base_path, "system_prompt.json")
        if os.path.exists(system_prompt_path):
            try:
                with open(system_prompt_path, "r", encoding="utf-8") as f:
                    system_prompts = json.load(f)
                enhancer_modes = list(system_prompts.keys())
            except Exception:
                enhancer_modes = ["standard"]
        else:
            enhancer_modes = ["standard"]

        # --- identities.json ---
        identities_path = os.path.join(base_path, "identities.json")
        if os.path.exists(identities_path):
            try:
                with open(identities_path, "r", encoding="utf-8") as f:
                    identities = json.load(f)
                identity_profiles = ["none", "external"] + list(identities.keys())
            except Exception:
                identity_profiles = ["none", "external"]
        else:
            identity_profiles = ["none", "external"]

        return {
            "required": {
                "json_name": (sorted(json_files),),
                "camera_angle": (camera_angle_list,),
                "camera_light": (camera_light_list,),     # ✅ NEW
                "daytime": (daytime_list,),               # ✅ NEW

                "use_enhancer": (["none", "ollama", "llamacpp", "openai", "cohere", "gemini"],),
                "enhancer_mode": (enhancer_modes,),
                "system_prompt_lock": (["auto", "external"], {"default": "auto"}),

                # ✅ NEW: enhancer words controls
                "enhancer_words_mode": (["auto", "min", "max"], {"default": "auto"}),
                "enhancer_words_min": ("INT", {"default": 140, "min": 40, "max": 400, "step": 5}),
                "enhancer_words_max": ("INT", {"default": 220, "min": 40, "max": 600, "step": 5}),

                "add_symbols": (["no", "yes"],),
                "seed": ("INT", {"default": 0}),
                "gender": (["neutral", "female", "2 female", "3 female", "female vampire", "anime woman", "male", "custom"],),

                "identity_profile": (identity_profiles,),
                "external_identity": ("STRING", {"default": "", "multiline": True, "forceInput": True}),
                "lock_identity": (["no", "yes"], {"default": "yes"}),

                "custom_intro": ("STRING", {"default": "", "multiline": True}),
                "custom_intro_id": (["Random", "0", "1", "2", "3", "4", "5", "6"], {"default": "Random"}),

                "horror_intensity": (["auto"] + [str(i) for i in range(11)],),
                "sensuality_level": (["auto", "0", "1", "2", "3"],),

                "pose_mode": (["random", "world_pick", "lock"], {"default": "random"}),
                "pose_index": ("INT", {"default": 0, "min": 0, "max": 200, "step": 1}),
                "show_pose_preview": ("BOOLEAN", {"default": True}),

                "lora_triggers": ("STRING", {"default": ""}),
                "subject_count": (["1", "2", "3"],),
                "lock_last_prompt": (["no", "yes"], {"default": "no"}),

                "multi_object_count": ("INT", {"default": 1, "min": 1, "max": 5}),

                # Ollama settings
                "ollama_host": ("STRING", {"default": "http://10.10.10.2:11434"}),
                "ollama_model": ("STRING", {"default": "qwen3:8b"})
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "pose_preview")
    FUNCTION = "generate_prompt"
    CATEGORY = "Prompt Creator"

    # ---------- Loaders ----------
    def _system_prompts(self):
        system_prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.json")
        if os.path.exists(system_prompt_path):
            try:
                with open(system_prompt_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
            except Exception:
                pass

        # fallback
        return {
            "standard": (
                "You are a professional prompt enhancer for AI image generation. "
                "Return ONE long, multi-clause sentence (~120–160 words), richly descriptive. "
                "Cover: genre/style; era; foreground/midground/background; materials & textures; color palette (3–5 tones); "
                "lighting (type/direction/intensity); atmosphere; camera angle & lens (mm); composition rule; 3–5 post-process keywords. "
                "No story, no dialogue, no lists, no headings."
            )
        }

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

    def _load_map_json(self, filename, default_ids=None):
        """
        Loads a json shaped like:
        { "ids": [...], "map": { "id": "text", ... } }
        """
        base = os.path.dirname(__file__)
        path = os.path.join(base, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    ids = data.get("ids", [])
                    mp = data.get("map", {})
                    if not isinstance(ids, list):
                        ids = []
                    if not isinstance(mp, dict):
                        mp = {}
                    return {"ids": ids, "map": mp}
            except Exception:
                pass
        return {"ids": default_ids or [], "map": {}}

    @staticmethod
    def _is_none(v):
        return (not v) or (str(v).strip().lower() == "none")

    def _resolve_mapped_value(self, ui_value, world_data, mapper_dict, world_keys):
        """
        Generic resolver:
        - If UI value is set (not none) => use it
        - Else try world keys in order
        - Map id through mapper_dict["map"] if available
        """
        chosen = ""
        if not self._is_none(ui_value):
            chosen = str(ui_value).strip()
        else:
            if isinstance(world_data, dict):
                for k in world_keys:
                    v = world_data.get(k)
                    if isinstance(v, str) and v.strip():
                        chosen = v.strip()
                        break

        if not chosen:
            return ""

        mapped = (mapper_dict or {}).get("map", {}).get(chosen)
        return mapped or chosen

    def _sanitize_world_keys(self, world_data, ui_value, keys_to_remove):
        if not self._is_none(ui_value) and isinstance(world_data, dict):
            wd = dict(world_data)
            for k in keys_to_remove:
                wd.pop(k, None)
            return wd
        return world_data

    # ---------- Prompt builder ----------
    def _build_prompt_from_json(
        self,
        data,
        gender,
        custom_intro,
        custom_intro_id,
        horror_intensity,
        sensuality_level,
        subject_count,
        multi_object_count,
        camera_angle_txt="",
        camera_light_txt="",
        daytime_txt="",
    ):
        parts = []

        # 1) Director-level controls in head (order matters)
        if isinstance(camera_angle_txt, str) and camera_angle_txt.strip():
            parts.append(camera_angle_txt.strip())
        if isinstance(camera_light_txt, str) and camera_light_txt.strip():
            parts.append(camera_light_txt.strip())
        if isinstance(daytime_txt, str) and daytime_txt.strip():
            parts.append(daytime_txt.strip())

        # 2) Gender / intro
        if gender == "custom":
            ci = (custom_intro or "").strip()

            def _get_custom_intro_pool(world_data):
                pool = {}
                raw = None
                if isinstance(world_data, dict):
                    raw = world_data.get("CUSTOM_INTRO") or world_data.get("custom_intro")

                if isinstance(raw, dict):
                    for k in [str(i) for i in range(7)]:
                        v = raw.get(k)
                        if isinstance(v, str) and v.strip():
                            pool[k] = v.strip()
                elif isinstance(raw, list):
                    for i in range(min(7, len(raw))):
                        v = raw[i]
                        if isinstance(v, str) and v.strip():
                            pool[str(i)] = v.strip()
                return pool

            if not ci:
                pool = _get_custom_intro_pool(data)

                if custom_intro_id and custom_intro_id != "Random":
                    chosen = pool.get(str(custom_intro_id))
                    if chosen:
                        ci = chosen

                if not ci and pool:
                    ci = random.choice(list(pool.values()))

            if ci:
                parts.append(ci)

        else:
            gender_inserted = False
            if isinstance(data, dict) and gender in data:
                values = data[gender]
                if isinstance(values, list) and values:
                    parts.append(random.choice(values))
                    gender_inserted = True

            if not gender_inserted:
                gender_defaults = {
                    "male": "a mysterious man",
                    "female": "a beautiful woman",
                    "2 female": "two beautiful women",
                    "3 female": "three unique beautiful women",
                    "female vampire": "a beautiful vampire woman",
                    "anime woman": "a beautiful anime woman",
                }
                parts.append(gender_defaults.get(gender, "a striking figure"))

        # Optional color realm
        color_realm_value = None
        if isinstance(data, dict) and "COLOR_REALM" in data:
            possible_realms = data["COLOR_REALM"]
            if isinstance(possible_realms, list) and possible_realms:
                color_realm_value = random.choice(possible_realms)
                parts.append(color_realm_value)

        multi_keys = ["OBJECTS", "ACCESSORIES"]

        # Pick values according to realm or flat lists
        if color_realm_value and isinstance(data, dict):
            for key in ["OUTFITS", "LIGHTING", "BACKGROUNDS", "OBJECTS", "ACCESSORIES", "ATMOSPHERES"]:
                values_by_realm = data.get(key, {}).get(color_realm_value, [])
                if isinstance(values_by_realm, list) and values_by_realm:
                    if key in multi_keys:
                        sampled = random.sample(values_by_realm, min(multi_object_count, len(values_by_realm)))
                        parts.extend(sampled)
                    else:
                        parts.append(random.choice(values_by_realm))
        else:
            if isinstance(data, dict):
                for key, values in data.items():
                    if key.lower() in [
                        "male", "female", "neutral",
                        "horror_intensity", "sensuality_level",
                        "color_realm",
                        "system_prompt", "world_name",
                        "custom_intro",
                        "camera_angles", "camera_angle",
                        "camera_light", "daytime",
                        "poses"
                    ]:
                        continue
                    if isinstance(values, list) and values:
                        if key in multi_keys:
                            sampled = random.sample(values, min(multi_object_count, len(values)))
                            parts.extend(sampled)
                        else:
                            parts.append(random.choice(values))

        # Horror intensity
        if horror_intensity != "auto" and isinstance(data, dict) and "HORROR_INTENSITY" in data:
            try:
                horror_level = int(horror_intensity)
                intensity_entries = data["HORROR_INTENSITY"]
                if isinstance(intensity_entries, dict):
                    matching = intensity_entries.get(str(horror_level))
                    if matching:
                        parts.append(matching)
            except ValueError:
                pass

        # Sensuality level
        if sensuality_level != "auto" and isinstance(data, dict) and "SENSUALITY_LEVEL" in data:
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

        return ", ".join([p for p in parts if isinstance(p, str) and p.strip()])

    # ---------- API Keys ----------
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

    # ---------- Enhancers ----------
    def _enhance_with_ollama(self, host, model, system_prompt, user_prompt):
        r = requests.post(
            f"{host}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            },
            timeout=120
        )
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
        """
        llama.cpp server backend.
        Tries OpenAI-compatible endpoint first (/v1/chat/completions), then falls back to (/completion).
        host example: http://127.0.0.1:11434
        """
        host = (host or "").rstrip("/")

        # 1) Try OpenAI-compatible chat endpoint
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

        # 2) Fallback to llama.cpp native /completion
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
            print("[PromptCreator] Cohere SDK not installed, skipping enhance.")
            return user_prompt

        keys = self._read_api_keys(base_path)
        api_key = keys.get("cohere", "").strip()
        if not api_key:
            print("[PromptCreator] No Cohere API key found, skipping enhance.")
            return user_prompt

        try:
            co = cohere.ClientV2(api_key=api_key)
        except Exception as e:
            print(f"[PromptCreator] Cohere ClientV2 not available: {e}")
            return user_prompt

        user_msg = (
            f"Seed: {user_prompt}\n\n"
            "Return exactly one long sentence (no line breaks)."
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
                return user_prompt

            content = re.sub(r"\s*\n+\s*", " ", content).strip()
            return content

        except Exception as e:
            print(f"[PromptCreator] Error calling Cohere chat: {e}")
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

    # ---------- Logging ----------
    @staticmethod
    def log_prompt_run(
        json_name,
        enhancer_mode,
        gender,
        custom_intro,
        lora_triggers,
        final_prompt,
        source="generated",
        node_version="1.11.0",
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

    # ---------- Enhancer words ----------
    @staticmethod
    def _build_enhancer_user_prompt(seed_prompt, words_mode, wmin, wmax):
        """
        words_mode:
          - auto: don't force range
          - min : force shorter range around wmin
          - max : force longer range up to wmax
        """
        base = (seed_prompt or "").strip()
        if not base:
            return "Enhance this prompt."

        # sanitize ints
        try:
            wmin = int(wmin)
        except Exception:
            wmin = 140
        try:
            wmax = int(wmax)
        except Exception:
            wmax = 220

        wmin = max(20, min(wmin, 600))
        wmax = max(20, min(wmax, 800))
        if wmax < wmin:
            wmax = wmin

        mode = (words_mode or "auto").strip().lower()

        if mode == "min":
            lo = max(20, wmin - 10)
            hi = max(lo + 10, wmin + 20)
            return (
                f"Enhance this prompt into ONE single long sentence (~{lo}–{hi} words), "
                f"no lists and no line breaks: {base}"
            )

        if mode == "max":
            lo = max(30, wmax - 30)
            hi = max(lo + 10, wmax)
            return (
                f"Enhance this prompt into ONE single long sentence (~{lo}–{hi} words), "
                f"no lists and no line breaks: {base}"
            )

        # auto
        return f"Enhance this prompt: {base}"

    # ---------- Main ----------
    def generate_prompt(
        self,
        json_name,
        camera_angle,
        camera_light,      # ✅ NEW
        daytime,           # ✅ NEW
        use_enhancer,
        enhancer_mode,
        system_prompt_lock,
        enhancer_words_mode,  # ✅ NEW
        enhancer_words_min,   # ✅ NEW
        enhancer_words_max,   # ✅ NEW
        add_symbols,
        seed,
        gender,
        identity_profile,
        external_identity,
        lock_identity,
        custom_intro,
        custom_intro_id,
        horror_intensity,
        sensuality_level,
        pose_mode,
        pose_index,
        show_pose_preview,
        lora_triggers,
        subject_count,
        lock_last_prompt,
        multi_object_count,
        ollama_host,
        ollama_model
    ):
        base_path = os.path.dirname(__file__)
        json_path = os.path.join(base_path, "JSON_DATA", json_name)

        # history lock
        history_dir = os.path.join(base_path, "history")
        os.makedirs(history_dir, exist_ok=True)
        history_path = os.path.join(history_dir, f"last_prompt_{json_name}.txt")

        if lock_last_prompt == "yes" and os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                prompt = f.read().strip()
            pose_preview = ""  # best-effort (history has no pose preview)
            self.log_prompt_run(
                json_name=json_name,
                enhancer_mode=enhancer_mode,
                gender=gender,
                custom_intro=custom_intro,
                lora_triggers=lora_triggers,
                final_prompt=prompt,
                source="history_lock",
                node_version=self.NODE_VERSION
            )
            print("[PromptCreator] Prompt locked and loaded from history")
            return (prompt, pose_preview)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[PromptCreator] Errore nel caricamento del JSON: {e}")
            return ("", "")

        # world-level SYSTEM_PROMPT (unified JSON) if present
        world_system_prompt = None
        if isinstance(data, dict):
            wsp = data.get("SYSTEM_PROMPT") or data.get("system_prompt")
            if isinstance(wsp, str) and wsp.strip():
                world_system_prompt = wsp.strip()

        # Load director maps
        angle_dict = self._load_map_json("camera_angles.json", default_ids=["front"])
        light_dict = self._load_map_json("camera_light.json", default_ids=[])
        daytime_dict = self._load_map_json("daytime.json", default_ids=[])

        # Resolve director values (UI overrides world)
        camera_angle_txt = self._resolve_mapped_value(camera_angle, data, angle_dict, ["camera_angle", "CAMERA_ANGLE"])
        camera_light_txt = self._resolve_mapped_value(camera_light, data, light_dict, ["camera_light", "CAMERA_LIGHT"])
        daytime_txt = self._resolve_mapped_value(daytime, data, daytime_dict, ["daytime", "DAYTIME"])

        # Sanitize world keys if overridden by UI
        data = self._sanitize_world_keys(data, camera_angle, ["camera_angle", "CAMERA_ANGLE"])
        data = self._sanitize_world_keys(data, camera_light, ["camera_light", "CAMERA_LIGHT"])
        data = self._sanitize_world_keys(data, daytime, ["daytime", "DAYTIME"])

        # Seed
        if seed:
            random.seed(seed)

        # Identity profile (prompt-only)
        identity_txt = ""
        if lock_identity == "yes":
            if identity_profile == "external":
                identity_txt = (external_identity or "").strip()
            elif identity_profile != "none":
                identities = self._identity_profiles()
                identity_txt = self._identity_to_text(identities.get(identity_profile, {}))

        # Build base prompt
        prompt = self._build_prompt_from_json(
            data=data,
            gender=gender,
            custom_intro=custom_intro,
            custom_intro_id=custom_intro_id,
            horror_intensity=horror_intensity,
            sensuality_level=sensuality_level,
            subject_count=subject_count,
            multi_object_count=multi_object_count,
            camera_angle_txt=camera_angle_txt,
            camera_light_txt=camera_light_txt,
            daytime_txt=daytime_txt,
        )

        # --- POSE CONTROL ---
        poses = []
        if isinstance(data, dict):
            poses = data.get("POSES") or data.get("poses") or []
        poses = poses if isinstance(poses, list) else []

        pose_preview = ""
        chosen_pose = ""
        pose_path = os.path.join(history_dir, f"last_pose_{json_name}.txt")

        def pick_pose_by_index(i):
            if not poses:
                return ""
            i = max(0, min(int(i), len(poses) - 1))
            return str(poses[i]).strip()

        if pose_mode == "world_pick":
            chosen_pose = pick_pose_by_index(pose_index)
        elif pose_mode == "lock":
            if os.path.exists(pose_path):
                with open(pose_path, "r", encoding="utf-8") as f:
                    chosen_pose = f.read().strip()
            if not chosen_pose:
                chosen_pose = pick_pose_by_index(pose_index)
        else:  # random
            if poses:
                chosen_pose = random.choice(poses).strip()

        if chosen_pose:
            prompt = prompt + ", " + chosen_pose
            with open(pose_path, "w", encoding="utf-8") as f:
                f.write(chosen_pose)

        if show_pose_preview:
            if poses:
                lines = [f"POSES ({len(poses)}):"]
                for i, p in enumerate(poses):
                    marker = " ->" if (chosen_pose and str(p).strip() == chosen_pose) else "   "
                    lines.append(f"{marker} {i}: {p}")
                pose_preview = "\n".join(lines)
            else:
                pose_preview = "POSES: (none found in this world JSON)"

        # Identity appended after pose (keeps face consistency late in chain)
        if identity_txt:
            prompt = prompt + ", " + identity_txt

        # System prompt selection
        system_prompts = self._system_prompts()
        effective_world_system_prompt = None if system_prompt_lock == "external" else world_system_prompt
        system_prompt = effective_world_system_prompt or system_prompts.get(enhancer_mode, system_prompts.get("standard", ""))

        # ✅ NEW: words-controlled user prompt for enhancer
        user_prompt = self._build_enhancer_user_prompt(
            seed_prompt=prompt,
            words_mode=enhancer_words_mode,
            wmin=enhancer_words_min,
            wmax=enhancer_words_max
        )

        # Enhancer backends
        if use_enhancer != "none":
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
                print(f"[PromptCreator] Errore nell'enhancer ({use_enhancer}): {e}")

        # LoRA triggers
        if isinstance(lora_triggers, str) and lora_triggers.strip():
            lts = [x.strip() for x in lora_triggers.split(",") if x.strip()]
            if lts:
                prompt += ", " + ", ".join(lts)

        if add_symbols == "yes":
            prompt = f"[{prompt}]"

        # Persist history
        with open(history_path, "w", encoding="utf-8") as f:
            f.write(prompt.strip())

        self.log_prompt_run(
            json_name=json_name,
            enhancer_mode=enhancer_mode,
            gender=gender,
            custom_intro=custom_intro,
            lora_triggers=lora_triggers,
            final_prompt=prompt,
            source="generated",
            node_version=self.NODE_VERSION
        )

        print(f"[PromptCreator] Prompt finale: {prompt}")
        return (prompt, pose_preview)
