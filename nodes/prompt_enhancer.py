# PromptEnhancerNode (ComfyUI)
# File: ComfyUI/custom_nodes/PromptEnhancerNode/__init__.py
#
# pip install requests
#
# Backends:
# - Ollama: /api/chat (preferred) with fallback to /api/generate (fixes Qwen3 cases)
# - llama.cpp server: /v1/chat/completions (OpenAI-compatible)
#
# Notes:
# - Ollama host example: http://10.10.10.2:11434
# - llama.cpp host example: http://127.0.0.1:8080

from __future__ import annotations

import re
from typing import Any, Dict, Tuple, List, Optional

import requests


def _strip_think_blocks_safe(text: str) -> str:
    """
    Removes <think>...</think> and <analysis>...</analysis> blocks.
    If removal empties the output, returns original text (better than empty).
    """
    if not text:
        return ""
    original = text.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", original, flags=re.S | re.I).strip()
    cleaned = re.sub(r"<analysis>.*?</analysis>", "", cleaned, flags=re.S | re.I).strip()
    return cleaned if cleaned else original


def _parse_stop_list(stop_csv: str) -> Optional[List[str]]:
    stop_csv = (stop_csv or "").strip()
    if not stop_csv:
        return None
    stops = [s.strip() for s in stop_csv.split(",") if s.strip()]
    return stops or None


class PromptEnhancerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ENGINE": (["ollama", "llama.cpp_server"], {"default": "ollama"}),

                "SYSTEM_PROMPT": (
                    "STRING",
                    {
                        "default": "You are a prompt enhancer. Return ONE single long, cinematic sentence in English, no lists, no line breaks.",
                        "multiline": True,
                    },
                ),
                "USER_PROMPT": ("STRING", {"default": "", "multiline": True}),

                "TEMPERATURE": ("FLOAT", {"default": 0.70, "min": 0.0, "max": 2.0, "step": 0.05}),
                "TOP_P": ("FLOAT", {"default": 0.90, "min": 0.0, "max": 1.0, "step": 0.01}),
                "MAX_TOKENS": ("INT", {"default": 240, "min": 1, "max": 4096, "step": 1}),
                "STRIP_THINKING": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                # Ollama
                "OLLAMA_HOST": ("STRING", {"default": "http://127.0.0.1:11434"}),
                "OLLAMA_MODEL": ("STRING", {"default": "qwen3:8b"}),

                # llama.cpp server
                "LLAMA_HOST": ("STRING", {"default": "http://127.0.0.1:8080"}),
                "LLAMA_MODEL": ("STRING", {"default": "local-model"}),

                # Shared
                "TIMEOUT": ("INT", {"default": 120, "min": 5, "max": 600, "step": 5}),
                "SEED": ("INT", {"default": -1, "min": -1, "max": 2_147_483_647, "step": 1}),
                "STOP": ("STRING", {"default": "", "multiline": False}),

                # Debug
                "DEBUG": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("ENHANCED_PROMPT",)
    FUNCTION = "enhance"
    CATEGORY = "TK/Prompt"

    # -------------------------
    # Ollama helpers
    # -------------------------
    def _ollama_chat(
        self,
        host: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        options: Dict[str, Any],
        timeout: int,
        debug: bool,
    ) -> Tuple[str, str]:
        host = (host or "").rstrip("/")
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": options or {},
        }

        if debug:
            print("[PFN Enhancer][Ollama][chat] POST", f"{host}/api/chat")
            print("[PFN Enhancer][Ollama][chat] model:", model)

        r = requests.post(f"{host}/api/chat", json=payload, timeout=int(timeout))
        r.raise_for_status()
        data = r.json()

        if isinstance(data, dict) and data.get("error"):
            return "", f"[OLLAMA CHAT ERROR] {data.get('error')}"

        content = ""
        if isinstance(data, dict):
            content = ((data.get("message") or {}).get("content")) or ""

        out = content.strip()

        if debug:
            print("[PFN Enhancer][Ollama][chat] out len:", len(out))
            if isinstance(data, dict):
                print("[PFN Enhancer][Ollama][chat] keys:", list(data.keys()))

        return out, ""

    def _ollama_generate(
        self,
        host: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        options: Dict[str, Any],
        timeout: int,
        debug: bool,
    ) -> Tuple[str, str]:
        host = (host or "").rstrip("/")
        payload: Dict[str, Any] = {
            "model": model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": options or {},
        }

        if debug:
            print("[PFN Enhancer][Ollama][generate] POST", f"{host}/api/generate")
            print("[PFN Enhancer][Ollama][generate] model:", model)

        r = requests.post(f"{host}/api/generate", json=payload, timeout=int(timeout))
        r.raise_for_status()
        data = r.json()

        if isinstance(data, dict) and data.get("error"):
            return "", f"[OLLAMA GENERATE ERROR] {data.get('error')}"

        content = ""
        if isinstance(data, dict):
            content = data.get("response") or ""

        out = content.strip()

        if debug:
            print("[PFN Enhancer][Ollama][generate] out len:", len(out))
            if isinstance(data, dict):
                print("[PFN Enhancer][Ollama][generate] keys:", list(data.keys()))

        return out, ""

    def _enhance_with_ollama(
        self,
        host: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        top_p: float,
        num_predict: int,
        timeout: int,
        seed: int,
        stop: str,
        debug: bool,
    ) -> str:
        host = (host or "").rstrip("/")
        url = f"{host}/api/chat"

        options: Dict[str, Any] = {
            "temperature": float(temperature),
            "top_p": float(top_p),
            "num_predict": int(num_predict),
        }
        if seed is not None and int(seed) >= 0:
            options["seed"] = int(seed)

        stops = _parse_stop_list(stop)
        if stops:
            options["stop"] = stops

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": False,          # ✅ CHIAVE per evitare thinking-only
            "options": options,
        }

        if debug:
            print("[Ollama] url:", url)
            print("[Ollama] model:", model)
            print("[Ollama] think:", payload.get("think"))
            print("[Ollama] options:", payload.get("options"))

        r = requests.post(url, json=payload, timeout=int(timeout))
        r.raise_for_status()
        data = r.json()

        # ✅ prende SOLO content
        out = ((data.get("message") or {}).get("content") or "").strip()

        # Se content è vuoto, ritorniamo un errore informativo (e NON silent empty)
        if not out:
            msg = data.get("message") or {}
            return (
                "[EMPTY OUTPUT] content empty.\n"
                f"done_reason={data.get('done_reason')}\n"
                f"content_len={len((msg.get('content') or ''))} thinking_len={len((msg.get('thinking') or ''))}\n"
                "Tip: ensure payload includes top-level think:false and num_predict is high enough."
            )

        return out




    # -------------------------
    # llama.cpp server backend (OpenAI-compatible)
    # -------------------------
    def _enhance_with_llama_server(
        self,
        host: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        top_p: float,
        max_tokens: int,
        timeout: int,
        seed: int,
        stop: str,
        debug: bool,
    ) -> str:
        host = (host or "").rstrip("/")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
        }

        if seed is not None and int(seed) >= 0:
            payload["seed"] = int(seed)

        stops = _parse_stop_list(stop)
        if stops:
            payload["stop"] = stops

        if debug:
            print("[PFN Enhancer][llama.cpp] POST", f"{host}/v1/chat/completions")
            print("[PFN Enhancer][llama.cpp] model:", model)

        r = requests.post(f"{host}/v1/chat/completions", json=payload, timeout=int(timeout))
        r.raise_for_status()
        data = r.json()

        try:
            choices = data.get("choices") or []
            if not choices:
                return "[EMPTY OUTPUT] llama.cpp returned no choices."
            msg = (choices[0].get("message") or {})
            out = (msg.get("content") or "").strip()
        except Exception:
            return f"[PARSE ERROR] Unexpected llama.cpp response shape: {str(data)[:300]}"

        if debug:
            print("[PFN Enhancer][llama.cpp] out len:", len(out))

        return out if out else "[EMPTY OUTPUT] llama.cpp returned empty content."

    # -------------------------
    # Node entry point (kwargs = anti-mismatch)
    # -------------------------
    def enhance(self, **kwargs) -> Tuple[str]:
        ENGINE = kwargs.get("ENGINE", "ollama")

        SYSTEM_PROMPT = (kwargs.get("SYSTEM_PROMPT", "") or "").strip()
        USER_PROMPT = (kwargs.get("USER_PROMPT", "") or "").strip()

        TEMPERATURE = float(kwargs.get("TEMPERATURE", 0.7))
        TOP_P = float(kwargs.get("TOP_P", 0.9))
        MAX_TOKENS = int(kwargs.get("MAX_TOKENS", 240))
        STRIP_THINKING = bool(kwargs.get("STRIP_THINKING", True))

        OLLAMA_HOST = kwargs.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        OLLAMA_MODEL = kwargs.get("OLLAMA_MODEL", "qwen3:8b")

        LLAMA_HOST = kwargs.get("LLAMA_HOST", "http://127.0.0.1:8080")
        LLAMA_MODEL = kwargs.get("LLAMA_MODEL", "local-model")

        TIMEOUT = int(kwargs.get("TIMEOUT", 120))
        SEED = int(kwargs.get("SEED", -1))
        STOP = (kwargs.get("STOP", "") or "").strip()

        DEBUG = bool(kwargs.get("DEBUG", False))

        if DEBUG:
            print("[PFN Enhancer] ENGINE:", ENGINE)
            print("[PFN Enhancer] USER_PROMPT len:", len(USER_PROMPT))
            print("[PFN Enhancer] SYSTEM_PROMPT len:", len(SYSTEM_PROMPT))
            print("[PFN Enhancer] OLLAMA:", OLLAMA_HOST, OLLAMA_MODEL)
            print("[PFN Enhancer] LLAMA :", LLAMA_HOST, LLAMA_MODEL)

        if not USER_PROMPT:
            return ("[EMPTY INPUT] USER_PROMPT is empty (possible name mismatch or upstream node output).",)

        if not SYSTEM_PROMPT:
            SYSTEM_PROMPT = "You are a prompt enhancer. Return ONE single long sentence."

        try:
            if ENGINE == "ollama":
                out = self._enhance_with_ollama(
                    OLLAMA_HOST,
                    OLLAMA_MODEL,
                    SYSTEM_PROMPT,
                    USER_PROMPT,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    num_predict=MAX_TOKENS,
                    timeout=TIMEOUT,
                    seed=SEED,
                    stop=STOP,
                    debug=DEBUG,
                )
            else:
                out = self._enhance_with_llama_server(
                    LLAMA_HOST,
                    LLAMA_MODEL,
                    SYSTEM_PROMPT,
                    USER_PROMPT,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    max_tokens=MAX_TOKENS,
                    timeout=TIMEOUT,
                    seed=SEED,
                    stop=STOP,
                    debug=DEBUG,
                )
        except requests.exceptions.RequestException as e:
            return (f"[NETWORK ERROR] {type(e).__name__}: {e}",)
        except Exception as e:
            return (f"[PromptEnhancerNode ERROR] {type(e).__name__}: {e}",)

        out = (out or "").strip()

        if STRIP_THINKING:
            out = _strip_think_blocks_safe(out)

        if not out:
            out = "[EMPTY OUTPUT] Output became empty after processing (try DEBUG=true)."

        return (out,)