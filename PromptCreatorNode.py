import os
import random
import json
import requests
from datetime import datetime

class PromptCreatorNode:
    @classmethod
    def INPUT_TYPES(cls):
        json_dir = os.path.join(os.path.dirname(__file__), "JSON_DATA")
        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]

        # camera angles (optional) from camera_angles.json
        camera_angle_list = ["none"]
        camera_angles_path = os.path.join(os.path.dirname(__file__), "camera_angles.json")
        if os.path.exists(camera_angles_path):
            try:
                with open(camera_angles_path, "r", encoding="utf-8") as f:
                    camera_data = json.load(f)
                ids = camera_data.get("ids", [])
                if isinstance(ids, list):
                    camera_angle_list += [str(x) for x in ids if str(x).strip()]
            except Exception:
                pass

        # carico le chiavi dal file esterno system_prompt.json
        system_prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.json")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_prompts = json.load(f)
            enhancer_modes = list(system_prompts.keys())
        else:
            enhancer_modes = ["standard"]

        # carico le chiavi dal file esterno identities.json (volto consistente)
        identities_path = os.path.join(os.path.dirname(__file__), "identities.json")
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
                "use_enhancer": (["none", "ollama","llamacpp", "openai", "cohere", "gemini"],),
                "enhancer_mode": (enhancer_modes,),
                "system_prompt_lock": (["auto", "external"], {"default": "auto"}),
                "add_symbols": (["no", "yes"],),
                "seed": ("INT", {"default": 0}),
                "gender": (["neutral", "female", "2 female", "3 female", "female vampire", "anime woman", "male", "custom"],),
                                "identity_profile": (identity_profiles,),
                "external_identity": ("STRING", {"default": "", "multiline": True, "forceInput": True}),
                "lock_identity": (["no", "yes"], {"default": "yes"}),
                "custom_intro": ("STRING", {"default": "", "multiline": True}),
                "custom_intro_id": (["Random","0","1","2","3","4","5","6"], {"default":"Random"}),
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

    RETURN_TYPES = ("STRING", "STRING")  # esempio
    RETURN_NAMES = ("prompt", "pose_preview")
    FUNCTION = "generate_prompt"
    CATEGORY = "Prompt Creator"

    def _system_prompts(self):
        system_prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.json")
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # fallback se manca il file
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
        """Carica i profili identità dal file identities.json (se presente)."""
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
        """Converte un profilo identità in una stringa descrittiva coerente (prompt-only)."""
        if not isinstance(identity_obj, dict):
            return ""
        order = ["age", "face_type", "eyes", "nose", "mouth", "hair", "skin", "expression_base"]
        chunks = []
        for k in order:
            v = identity_obj.get(k) or identity_obj.get(k.upper())
            if isinstance(v, str) and v.strip():
                chunks.append(v.strip())
        return ", ".join(chunks)



    def _camera_angles(self):
        path = os.path.join(os.path.dirname(__file__), "camera_angles.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"ids": ["front"], "map": {}}

    @staticmethod
    def _is_none(v):
        return (not v) or (str(v).strip().lower() == "none")

    def _resolve_camera_angle(self, ui_angle, world_data, angle_dict):
        """
        Se UI ha un valore (≠ none) → usa quello e ignora il mondo.
        Se UI è none → eredita da world_data["camera_angle"] o ["CAMERA_ANGLE"].
        Mappa l'id in camera_angles.map se presente, altrimenti lascia il testo.
        """
        if not self._is_none(ui_angle):
            chosen = ui_angle
        else:
            chosen = world_data.get("camera_angle") or world_data.get("CAMERA_ANGLE") or ""
        if not chosen:
            return ""
        mapped = (angle_dict or {}).get("map", {}).get(chosen)
        return mapped or chosen

    def _sanitize_world_camera(self, world_data, ui_angle):
        if not self._is_none(ui_angle) and world_data:
            wd = dict(world_data)
            wd.pop("camera_angle", None)
            wd.pop("CAMERA_ANGLE", None)
            return wd
        return world_data

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
    ):
        parts = []

        # 1) Camera angle (se presente) in testa
        if isinstance(camera_angle_txt, str) and camera_angle_txt.strip():
            parts.append(camera_angle_txt.strip())

        # 2) Gender / subject intro
        # Se gender=custom:
        # - se custom_intro (textarea) non è vuoto -> usa quello (override manuale)
        # - altrimenti usa custom_intro_id (0..6 o Random) dal world JSON (CUSTOM_INTRO come dict o list)
        if gender == "custom":
            ci = (custom_intro or "").strip()

            def _get_custom_intro_pool(world_data):
                pool = {}
                raw = None
                if isinstance(world_data, dict):
                    raw = world_data.get("CUSTOM_INTRO") or world_data.get("custom_intro")

                # dict -> keys "0".."6"
                if isinstance(raw, dict):
                    for k in [str(i) for i in range(7)]:
                        v = raw.get(k)
                        if isinstance(v, str) and v.strip():
                            pool[k] = v.strip()

                # list -> indices 0..6
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
                    "2 female": "two beautiful womans",
                    "3 female": "three unique beautiful womans",
                    "female vampire": "a beautiful vampire woman",
                    "anime woman": "a beautiful anime woman",
                }
                parts.append(gender_defaults.get(gender, "a striking figure"))

        # Optional color realm


        color_realm_value = None
        if "COLOR_REALM" in data:
            possible_realms = data["COLOR_REALM"]
            if isinstance(possible_realms, list) and possible_realms:
                color_realm_value = random.choice(possible_realms)
                print(f"[PromptCreator] Using COLOR_REALM: {color_realm_value}")
                parts.append(color_realm_value)

        multi_keys = ["OBJECTS", "ACCESSORIES"]

        # Pick values according to realm or flat lists
        if color_realm_value:
            for key in ["OUTFITS", "LIGHTING", "BACKGROUNDS", "OBJECTS", "ACCESSORIES", "ATMOSPHERES"]:
                values_by_realm = data.get(key, {}).get(color_realm_value, [])
                if isinstance(values_by_realm, list) and values_by_realm:
                    if key in multi_keys:
                        sampled = random.sample(values_by_realm, min(multi_object_count, len(values_by_realm)))
                        parts.extend(sampled)
                    else:
                        parts.append(random.choice(values_by_realm))
        else:
            for key, values in data.items():
                if key.lower() in [
                    "male", "female", "neutral",
                    "horror_intensity", "sensuality_level",
                    "color_realm",
                    "system_prompt", "world_name",
                    "custom_intro",
                    "camera_angles", "camera_angle",
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

        # Sensuality level (modulatore simile a HORROR_INTENSITY)
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

        return ", ".join(parts)

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

    def _enhance_with_ollama(self, host, model, system_prompt, user_prompt):
        # Prefer chat to support system role
        r = requests.post(f"{host}/api/chat", json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "think": False,
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

    import requests

    def _enhance_with_llamacpp(self, host, system_prompt, user_prompt, temperature=0.7, top_p=0.9, n_predict=220):
        """
        llama.cpp server backend.
        Tries OpenAI-compatible endpoint first (/v1/chat/completions), then falls back to (/completion).
        host example: http://127.0.0.1:11434
        """

        host = host.rstrip("/")

        # 1) Try OpenAI-compatible chat endpoint
        try:
            r = requests.post(
                f"{host}/v1/chat/completions",
                json={
                    "model": "llama",  # ignored by llama.cpp in many builds; kept for compatibility
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
                # OpenAI-like: choices[0].message.content
                content = (
                    j.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                content = (content or "").strip()
                if content:
                    return content

            # if non-200, fall through to fallback
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

        # llama.cpp /completion commonly returns: {"content": "..."} or {"completion": "..."} depending on version
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

        # Usa il client V2 (nuova API)
        try:
            co = cohere.ClientV2(api_key=api_key)
        except Exception as e:
            print(f"[PromptCreator] Cohere ClientV2 not available: {e}")
            return user_prompt

        # Messaggi Chat v2
        system_msg = (
            f"{system_prompt}\n\n"
            "You are a prompt enhancer for image generation. "
            "Expand the user seed into ONE single, long, flowing sentence "
            "with multiple clauses separated by commas and semicolons. "
            "Do NOT use bullet points or numbered lists. "
            "Keep the original mood and style."
        )

        user_msg = (
            f"Seed: {user_prompt}\n\n"
            "Return exactly one long sentence (around 100 to 150 words), no line breaks."
        )

        # === BLOCCO TRY PRINCIPALE ===
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
                print("[PromptCreator] Cohere returned empty content.")
                return user_prompt

            content = re.sub(r"\s*\n+\s*", " ", content).strip()
            return content

        # === ECCO IL BLOCCO EXCEPT CHE ORA È ALLINEATO PERFETTAMENTE ===
        except Exception as e:
            print(f"[PromptCreator] Error calling Cohere chat: {e}")
            return user_prompt


    def _enhance_with_gemini(self, base_path, system_prompt, user_prompt):
        import google.generativeai as genai
        keys = self._read_api_keys(base_path)
        genai.configure(api_key=keys.get("gemini", ""))
        # In Gemini, passiamo tutto come testo
        model = genai.GenerativeModel("models/gemini-2.5-pro")
        txt = (
            f"SYSTEM: {system_prompt}\n"
            f"USER: {user_prompt}\n"
            "Return only the final prompt as a single paragraph."
        )
        r = model.generate_content(txt)
        return r.candidates[0].content.parts[0].text.strip()

    @staticmethod
    def log_prompt_run(
        json_name,
        enhancer_mode,
        gender,
        custom_intro,
        lora_triggers,
        final_prompt,
        source="generated",
        node_version="1.5.0",
    ):
        """Append one JSONL entry per run to ./logs/prompt_history.jsonl."""
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



    
    def generate_prompt(self, json_name, camera_angle, use_enhancer, enhancer_mode, system_prompt_lock, add_symbols, seed, gender, identity_profile, external_identity, lock_identity, custom_intro, custom_intro_id, horror_intensity, sensuality_level, pose_mode, pose_index, show_pose_preview, lora_triggers, subject_count, lock_last_prompt, multi_object_count, ollama_host, ollama_model):
        base_path = os.path.dirname(__file__)
        json_path = os.path.join(base_path, "JSON_DATA", json_name)

        # history lock
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
                node_version="1.5.0"
            )
            print("[PromptCreator] Prompt locked and loaded from history")
            return (prompt, )

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[PromptCreator] Errore nel caricamento del JSON: {e}")
            return ("",)

        # world-level SYSTEM_PROMPT (unified JSON) if present
        world_system_prompt = None
        if isinstance(data, dict):
            wsp = data.get("SYSTEM_PROMPT") or data.get("system_prompt")
            if isinstance(wsp, str) and wsp.strip():
                world_system_prompt = wsp.strip()
        # Camera angle resolution (UI overrides world)
        angle_dict = self._camera_angles()
        camera_angle_txt = self._resolve_camera_angle(camera_angle, data, angle_dict)
        data = self._sanitize_world_camera(data, camera_angle)

        # Seed opzionale per coerenza
        if seed:
            random.seed(seed)

        # Identity profile (prompt-only consistency)
        identity_txt = ""
        if lock_identity == "yes":
            if identity_profile == "external":
                identity_txt = (external_identity or "").strip()
            elif identity_profile != "none":
                identities = self._identity_profiles()
                identity_txt = self._identity_to_text(identities.get(identity_profile, {}))
            print("[PromptCreator][DEBUG] identity_profile:", identity_profile)
            print("[PromptCreator][DEBUG] lock_identity:", lock_identity)
            print("[PromptCreator][DEBUG] identity_txt:", repr(identity_txt))



        # Costruisci prompt base
        prompt = self._build_prompt_from_json(
            data, gender, custom_intro, custom_intro_id, horror_intensity, sensuality_level, subject_count, multi_object_count, camera_angle_txt=camera_angle_txt
        )
                # --- POSE CONTROL ---
        poses = data.get("POSES") or data.get("poses") or []
        poses = poses if isinstance(poses, list) else []
        pose_preview = ""
        chosen_pose = ""
       
        if show_pose_preview and poses:
            lines = [f"POSES ({len(poses)}):"]
            for i, p in enumerate(poses):
                marker = " ->" if (chosen_pose and str(p).strip() == chosen_pose) else "   "
                lines.append(f"{marker} {i}: {p}")
            pose_preview = "\n".join(lines)
        elif show_pose_preview:
            pose_preview = "POSES: (none found in this world JSON)"

        pose_path = os.path.join(base_path, "history", f"last_pose_{json_name}.txt")

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
            os.makedirs(os.path.dirname(pose_path), exist_ok=True)
            with open(pose_path, "w", encoding="utf-8") as f:
                f.write(chosen_pose)
        # --- END POSE CONTROL ---

        if identity_txt:
            prompt = prompt + ", " + identity_txt
            print("[PromptCreator][DEBUG] prompt_pre_enhancer:", prompt)


        # System prompt condiviso per tutti i backend
        system_prompts = self._system_prompts()
        effective_world_system_prompt = None if system_prompt_lock == "external" else world_system_prompt
        system_prompt = effective_world_system_prompt or system_prompts.get(enhancer_mode, system_prompts["standard"])
        user_prompt = f"Enhance this prompt: {prompt}"

        # Enhancer backends
        if use_enhancer != "none":
            print("[PromptCreator][DEBUG] use_enhancer:", use_enhancer)
            print("[PromptCreator][DEBUG] enhancer_mode:", enhancer_mode)
            print("[PromptCreator][DEBUG] system_prompt:", system_prompt)
            print("[PromptCreator][DEBUG] user_prompt:", user_prompt)

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
        if lora_triggers.strip():
            lts = [x.strip() for x in lora_triggers.split(",") if x.strip()]
            if lts:
                prompt += ", " + ", ".join(lts)
                print(f"[PromptCreator] LoRA triggers aggiunti: {lts}")

        if add_symbols == "yes":
            prompt = f"[{prompt}]"

        os.makedirs(os.path.join(base_path, "history"), exist_ok=True)
        with open(history_path, "w", encoding="utf-8") as f:
            f.write(prompt.strip())

        print(f"[PromptCreator] Prompt finale: {prompt}")
        self.log_prompt_run(
            json_name=json_name,
            enhancer_mode=enhancer_mode,
            gender=gender,
            custom_intro=custom_intro,
            lora_triggers=lora_triggers,
            final_prompt=prompt,
            source="generated",
                node_version="1.5.0"
        )
        return (prompt, pose_preview)
