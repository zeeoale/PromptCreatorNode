import os
import random
import json

class PromptCreatorNode:
    @classmethod
    def INPUT_TYPES(cls):
        json_dir = os.path.join(os.path.dirname(__file__), "JSON_DATA")
        json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]

        return {
            "required": {
                "json_name": (sorted(json_files),),
                "use_enhancer": (["none", "openai", "cohere", "gemini"],),
                "add_symbols": (["no", "yes"],),
                "seed": ("INT", {"default": 0}),
                "gender": (["neutral", "female", "male"],),
                "horror_intensity": (["auto"] + [str(i) for i in range(11)],),
                "lora_triggers": ("STRING", {"default": ""}),
                "subject_count": (["1", "2", "3"], {"default": "1"}),
                "lock_last_prompt": (["no", "yes"], {"default": "no"})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate_prompt"
    CATEGORY = "Prompt Creator"

    def generate_prompt(self, json_name, use_enhancer, add_symbols, seed,  gender, horror_intensity, lora_triggers, subject_count, lock_last_prompt):
        base_path = os.path.dirname(__file__)
        json_path = os.path.join(base_path, "JSON_DATA", json_name)

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

        parts = []

        gender_inserted = False
        if gender in data:
            values = data[gender]
            if isinstance(values, list) and values:
                parts.append(random.choice(values))
                gender_inserted = True
        if not gender_inserted:
            if gender == "male":
                parts.append("a mysterious man")
            elif gender == "female":
                parts.append("a beautiful woman")
            else:
                parts.append("a striking figure")

        color_realm_value = None
        if "COLOR_REALM" in data:
            possible_realms = data["COLOR_REALM"]
            if isinstance(possible_realms, list) and possible_realms:
                color_realm_value = random.choice(possible_realms)
                print(f"[PromptCreator] Using COLOR_REALM: {color_realm_value}")
                parts.append(color_realm_value)

        if color_realm_value:
            for key in ["OUTFITS", "LIGHTING", "BACKGROUNDS", "OBJECTS", "ACCESSORIES", "ATMOSPHERES"]:
                values_by_realm = data.get(key, {}).get(color_realm_value, [])
                if isinstance(values_by_realm, list) and values_by_realm:
                    parts.append(random.choice(values_by_realm))
        else:
            for key, values in data.items():
                if key.lower() in ["male", "female", "neutral", "horror_intensity", "color_realm"]:
                    continue
                if isinstance(values, list) and values:
                    parts.append(random.choice(values))

        horror_level = None
        if horror_intensity != "auto":
            try:
                horror_level = int(horror_intensity)
            except ValueError:
                horror_level = None

        if horror_level is not None and "HORROR_INTENSITY" in data:
            intensity_entries = data["HORROR_INTENSITY"]
            if isinstance(intensity_entries, dict):
                matching = intensity_entries.get(str(horror_level))
                if matching:
                    parts.append(matching)

        if subject_count != "1":
            parts.append(f"{subject_count} subjects present")

        prompt = ", ".join(parts)

        if use_enhancer != "none":
            try:
                keys_path = os.path.join(base_path, "api_keys.txt")
                keys = {}
                with open(keys_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line:
                            k, v = line.strip().split("=", 1)
                            keys[k.strip()] = v.strip()

                if use_enhancer == "openai":
                    import openai
                    openai.api_key = keys.get("openai", "")
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You're an expert prompt engineer."},
                            {"role": "user", "content": f"Enhance this prompt for image generation: {prompt}"}
                        ]
                    )
                    prompt = response.choices[0].message.content.strip()

                elif use_enhancer == "cohere":
                    import cohere
                    co = cohere.Client(keys.get("cohere", ""))
                    response = co.generate(
                        model="command-r-plus",
                        prompt=f"Create a simple yet detailed prompt for image generation:\n{prompt}",
                        max_tokens=200
                    )
                    prompt = response.generations[0].text.strip()

                elif use_enhancer == "gemini":
                    import google.generativeai as genai
                    genai.configure(api_key=keys.get("gemini", ""))
                    model = genai.GenerativeModel("models/gemini-2.5-pro")
                    prompt_text = f"""
You're an expert prompt engineer for Stable Diffusion AI image generation.

Enhance the following concept into a vivid, cinematic, emotionally intense, and descriptive scene, using rich visual language. Include environmental details, camera angle, lighting, and mood. Return the result as a single paragraph only, no extra formatting.

Prompt: {prompt}

Enhanced:
"""
                    with open(os.path.join(base_path, "debug_gemini_prompt.txt"), "w", encoding="utf-8") as debug_file:
                        debug_file.write(prompt_text)

                    try:
                        response = model.generate_content(prompt_text)
                        print(f"[PromptCreator] Gemini raw response: {response}")
                        print(f"[PromptCreator] Gemini response type: {type(response)}")
                        enhanced_text = response.candidates[0].content.parts[0].text.strip()
                        if not enhanced_text:
                            raise ValueError("Empty response from Gemini")
                        prompt = enhanced_text
                    except Exception as e:
                        print(f"[PromptCreator] Errore nell'enhancer Gemini: {e}")
            except Exception as e:
                print(f"[PromptCreator] Errore nell'enhancer: {e}")

        lora_trigger_list = []
        if lora_triggers.strip():
            lora_trigger_list = [x.strip() for x in lora_triggers.strip().split(",") if x.strip()]
            prompt += ", " + ", ".join(lora_trigger_list)
            print(f"[PromptCreator] LoRA triggers aggiunti dopo enhancement: {lora_trigger_list}")

        if add_symbols == "yes":
            prompt = f"[{prompt}]"

        os.makedirs(os.path.join(base_path, "history"), exist_ok=True)
        with open(history_path, "w", encoding="utf-8") as f:
            f.write(prompt.strip())

        print(f"[PromptCreator] Prompt finale: {prompt}")
        return (prompt,)
