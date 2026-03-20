import requests
import os


# =========================
# 🧠 CLEAN OUTPUT RULES
# =========================
CLEAN_OUTPUT_PROMPT = """
You must return ONLY the final refined prompt.

Do NOT include:
- explanations
- reasoning
- thinking
- analysis
- markdown formatting
- headings
- bullet points

Do not produce hidden reasoning or thinking tokens.
Do not include <think> or similar tags.

Output must be a single continuous paragraph.

No extra text before or after the prompt.

The output must be ready to use directly.
"""


class PromptRefinerNode:

    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    # =========================
    # 🔑 API KEYS (COME PCN)
    # =========================
    def _read_api_keys(self, base_path):
        keys_path = os.path.join(base_path, "api_keys.txt")
        keys = {}

        if os.path.exists(keys_path):
            with open(keys_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        keys[k.strip()] = v.strip()
        else:
            print(f"[PromptRefiner] api_keys.txt NOT FOUND at: {keys_path}")

        return keys

    # =========================
    # 🧩 INPUTS
    # =========================
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_in": ("STRING", {"multiline": True}),
                "enable_refine": ("BOOLEAN", {"default": True}),
                "provider": ([
                    "ollama",
                    "openrouter",
                    "openai",
                    "gemini",
                    "cohere",
                    "llama_cpp"
                ],),
                "refinement_mode": ([
                    "subtle",
                    "balanced",
                    "creative"
                ],),
            },
            "optional": {
                "model": ("STRING", {"default": ""}),
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "host": ("STRING", {"default": "http://127.0.0.1:11434"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt_out", "prompt_raw")
    FUNCTION = "refine"
    CATEGORY = "PFN / Prompt"

    # =========================
    # 🚀 MAIN
    # =========================
    def refine(self, prompt_in, enable_refine, provider, refinement_mode, model="", system_prompt="", host="http://127.0.0.1:11434"):

        if not enable_refine:
            return (prompt_in, prompt_in)

        base_prompt = system_prompt.strip() if system_prompt.strip() else self.get_default_system_prompt(refinement_mode)
        system_prompt_full = base_prompt + "\n\n" + CLEAN_OUTPUT_PROMPT

        try:
            raw_response = self.call_provider(
                provider,
                model,
                system_prompt_full,
                prompt_in,
                host
            )

            refined_prompt = self.extract_text(raw_response)

            # 🔥 DEBUG
            print("\n[PromptRefiner] FINAL PROMPT:\n")
            print(refined_prompt)
            print("\n" + "="*60 + "\n")

        except Exception as e:
            refined_prompt = prompt_in
            raw_response = f"ERROR: {str(e)}"
            print(f"[PromptRefiner ERROR] {e}")

        return (refined_prompt, raw_response)

    # =========================
    # 🧠 SYSTEM MODES
    # =========================
    def get_default_system_prompt(self, mode):

        if mode == "subtle":
            return "Refine the prompt preserving structure and improving clarity."

        elif mode == "balanced":
            return "Refine the prompt improving clarity, flow and visual richness while preserving identity."

        elif mode == "creative":
            return "Enhance the prompt with richer detail, atmosphere and depth while keeping the original concept intact."

        return ""

    # =========================
    # 🔌 ROUTER
    # =========================
    def call_provider(self, provider, model, system_prompt, user_prompt, host):

        if provider == "ollama":
            return self.call_ollama(model, system_prompt, user_prompt, host)

        elif provider == "llama_cpp":
            return self.call_llama_cpp(system_prompt, user_prompt, host)

        elif provider == "openrouter":
            return self._enhance_with_openrouter(self.base_path, model, system_prompt, user_prompt)

        elif provider == "openai":
            return f"[OpenAI NOT IMPLEMENTED]\n{user_prompt}"

        elif provider == "gemini":
            return f"[Gemini NOT IMPLEMENTED]\n{user_prompt}"

        elif provider == "cohere":
            return f"[Cohere NOT IMPLEMENTED]\n{user_prompt}"

        else:
            raise ValueError("Unsupported provider")

    # =========================
    # 🔌 OLLAMA
    # =========================
    def call_ollama(self, model, system_prompt, user_prompt, host):

        url = f"{host}/api/generate"

        payload = {
            "model": model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False
        }

        r = requests.post(url, json=payload)
        return r.json().get("response", "")

    # =========================
    # 🔌 LLAMA CPP
    # =========================
    def call_llama_cpp(self, system_prompt, user_prompt, host):

        url = f"{host}/completion"

        payload = {
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "temperature": 0.7,
            "max_tokens": 512
        }

        r = requests.post(url, json=payload)
        return r.json().get("content", "")

    # =========================
    # 🌐 OPENROUTER (PCN STYLE + SAFE)
    # =========================
    def _enhance_with_openrouter(self, base_path, model, system_prompt, user_prompt):

        keys = self._read_api_keys(base_path)
        api_key = keys.get("openrouter", "").strip()

        if not api_key:
            print("[PromptRefiner] ❌ No OpenRouter API key found.")
            return user_prompt

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )

            r.raise_for_status()

            data = r.json()

            print("\n[OpenRouter RAW RESPONSE]")
            print(data)
            print("="*60)

            # ✅ standard
            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()

            # ❗ fallback
            if "output" in data:
                return data["output"]

            if "content" in data:
                return data["content"]

            return str(data)

        except Exception as e:
            print(f"[PromptRefiner OpenRouter ERROR] {e}")
            return user_prompt

    # =========================
    # 🧹 CLEAN OUTPUT
    # =========================
    def extract_text(self, response):

        if not isinstance(response, str):
            return str(response)

        text = response.strip()

        if "<think>" in text:
            text = text.split("</think>")[-1]

        text = text.replace("<think>", "").replace("</think>", "")

        if "Prompt:" in text:
            text = text.split("Prompt:")[-1]

        text = " ".join(text.split())

        return text.strip()