import os
import random
import json
import requests

class PromptCreatorNode:
    @classmethod
    def INPUT_TYPES(cls):
        json_dir = os.path.join(os.path.dirname(__file__), "JSON_DATA")
        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]

        return {
            "required": {
                "json_name": (sorted(json_files),),
                "use_enhancer": (["none", "ollama", "openai", "cohere", "gemini"],),
                "enhancer_mode": (["standard", "dark_ritual", "aesthetic_focus", "compact"],),
                "add_symbols": (["no", "yes"],),
                "seed": ("INT", {"default": 0}),
                "gender": (["neutral", "female", "2 female", "3 female", "female vampire", "male", "custom"],),
                "custom_intro": ("STRING", {"default": "", "multiline": True}),
                "horror_intensity": (["auto"] + [str(i) for i in range(11)],),
                "lora_triggers": ("STRING", {"default": ""}),
                "subject_count": (["1", "2", "3"],),
                "lock_last_prompt": (["no", "yes"], {"default": "no"}),
                "multi_object_count": ("INT", {"default": 1, "min": 1, "max": 5}),
                # Ollama settings
                "ollama_host": ("STRING", {"default": "http://192.168.1.1:11434"}),
                "ollama_model": ("STRING", {"default": "llama3.2"})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate_prompt"
    CATEGORY = "Prompt Creator"

    def _system_prompts(self):
        return {
            "standard": (
                "You're a professional prompt enhancer for AI image generation. "
                "Return a vivid, well-written prompt as a single sentence. No notes, no lists."
            ),
            "dark_ritual": (
                "You're a cinematic horror stylist. Transform prompts into disturbing, poetic, gothic horror compositions in a single sentence."
            ),
            "aesthetic_focus": (
                "You're a fashion-forward visual stylist. Enhance with elegance, beauty, balance and chic atmosphere in a single sentence."
            ),
            "compact": (
                "You're an expert in minimal but expressive prompts. Return a short, dense prompt with strong visuals and no filler."
            ),
        }

    def _build_prompt_from_json(self, data, gender, custom_intro, horror_intensity, subject_count, multi_object_count):
        parts = []

        # Gender / subject intro
        if gender == "custom" and custom_intro.strip():
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
                    "female vampire": "a beautiful vampire woman"
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
                if key.lower() in ["male", "female", "neutral", "horror_intensity", "color_realm"]:
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

    def _enhance_with_cohere(self, base_path, system_prompt, user_prompt):
        import cohere
        keys = self._read_api_keys(base_path)
        co = cohere.Client(keys.get("cohere", ""))
        # Cohere "generate" non ha system; includiamo l'istruzione nel prompt
        resp = co.generate(
            model="command-r-plus",
            prompt=f"SYSTEM: {system_prompt}\nUSER: {user_prompt}\nReturn only the final prompt.",
            max_tokens=700
        )
        return resp.generations[0].text.strip()

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

    def generate_prompt(self, json_name, use_enhancer, enhancer_mode, add_symbols, seed, gender, custom_intro, horror_intensity, lora_triggers, subject_count, lock_last_prompt, multi_object_count, ollama_host, ollama_model):
        base_path = os.path.dirname(__file__)
        json_path = os.path.join(base_path, "JSON_DATA", json_name)

        # history lock
        history_path = os.path.join(base_path, "history", f"last_prompt_{json_name}.txt")
        if lock_last_prompt == "yes" and os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                prompt = f.read().strip()
            print("[PromptCreator] Prompt locked and loaded from history")
            return (prompt,)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[PromptCreator] Errore nel caricamento del JSON: {e}")
            return ("",)

        # Seed opzionale per coerenza
        if seed:
            random.seed(seed)

        # Costruisci prompt base
        prompt = self._build_prompt_from_json(
            data, gender, custom_intro, horror_intensity, subject_count, multi_object_count
        )

        # System prompt condiviso per tutti i backend
        system_prompts = self._system_prompts()
        system_prompt = system_prompts.get(enhancer_mode, system_prompts["standard"])
        user_prompt = f"Enhance this prompt: {prompt}"

        # Enhancer backends
        if use_enhancer != "none":
            try:
                if use_enhancer == "ollama":
                    prompt = self._enhance_with_ollama(ollama_host, ollama_model, system_prompt, user_prompt)
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
        return (prompt,)
