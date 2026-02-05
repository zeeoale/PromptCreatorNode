import os
import json
import re

class PromptReplayNode:
    """
    Prompt Replay (V2)
    - Reads ./logs/prompt_history.jsonl
    - Builds a human-friendly dropdown of recent entries
    - Lets you filter by source/json/lora/system
    - Outputs the exact final_prompt
    """

    # Cache to map dropdown labels -> entry dict
    _cache_options = []
    _cache_entries = []

    @staticmethod
    def _log_path():
        base_path = os.path.dirname(__file__)
        return os.path.join(base_path, "logs", "prompt_history.jsonl")

    @staticmethod
    def _normalize(s: str) -> str:
        return (s or "").strip()

    @staticmethod
    def _parse_triggers(lora_triggers):
        # stored as string in your logger; accept list too just in case
        if isinstance(lora_triggers, list):
            return [str(x).strip() for x in lora_triggers if str(x).strip()]
        if isinstance(lora_triggers, str):
            return [x.strip() for x in lora_triggers.split(",") if x.strip()]
        return []

    @classmethod
    def _load_entries(cls, max_entries: int, source_filter: str, json_filter: str, lora_filter: str, system_filter: str):
        path = cls._log_path()
        if not os.path.exists(path):
            cls._cache_options = ["(no prompt_history.jsonl found)"]
            cls._cache_entries = []
            return

        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                # source filter
                if source_filter != "all":
                    if data.get("source") != source_filter:
                        continue

                # json filter (substring, case-insensitive)
                jf = cls._normalize(json_filter).lower()
                if jf:
                    world = str(data.get("json_world", "")).lower()
                    if jf not in world:
                        continue

                # system filter (substring on enhancer_mode key)
                sf = cls._normalize(system_filter).lower()
                if sf:
                    sysmode = str(data.get("system_prompt", "")).lower()
                    if sf not in sysmode:
                        continue

                # lora filter (substring against triggers)
                lf = cls._normalize(lora_filter).lower()
                if lf:
                    triggers = ",".join(cls._parse_triggers(data.get("lora_triggers", ""))).lower()
                    if lf not in triggers:
                        continue

                entries.append(data)

        if not entries:
            cls._cache_options = ["(no entries match filters)"]
            cls._cache_entries = []
            return

        # take last N, most recent first
        entries = entries[-max_entries:][::-1]

        options = []
        for idx, e in enumerate(entries):
            ts = e.get("timestamp", "unknown-time")
            world = e.get("json_world", "unknown-json")
            sysmode = e.get("system_prompt", "standard")
            src = e.get("source", "generated")
            triggers = cls._parse_triggers(e.get("lora_triggers", ""))
            triggers_short = ""
            if triggers:
                # keep it readable
                show = triggers[:3]
                triggers_short = " | LoRA: " + ", ".join(show) + ("…" if len(triggers) > 3 else "")

            # label format: "0 | 2026-01-21T22:47:03 | Modern_Goth_Urban.json | enhancer_mode | generated | LoRA: ..."
            label = f"{idx} | {ts} | {world} | {sysmode} | {src}{triggers_short}"
            options.append(label)

        cls._cache_options = options
        cls._cache_entries = entries

    @classmethod
    def INPUT_TYPES(cls):
        # Defaults for initial cache build
        # Note: dropdown list updates when ComfyUI reloads nodes (or restart).
        cls._load_entries(
            max_entries=80,
            source_filter="all",
            json_filter="",
            lora_filter="",
            system_filter=""
        )
        return {
            "required": {
                "pick": (cls._cache_options if cls._cache_options else ["(empty)"],),
                "max_entries": ("INT", {"default": 80, "min": 1, "max": 500, "step": 1}),
                "source_filter": (["all", "generated", "history_lock"],),
                "json_filter": ("STRING", {"default": "", "multiline": False}),
                "lora_filter": ("STRING", {"default": "", "multiline": False}),
                "system_filter": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "meta")
    FUNCTION = "replay"
    CATEGORY = "Prompt Tools"

    def replay(self, pick, max_entries, source_filter, json_filter, lora_filter, system_filter):
        # Rebuild cache using current filters
        self.__class__._load_entries(
            max_entries=int(max_entries),
            source_filter=str(source_filter),
            json_filter=str(json_filter),
            lora_filter=str(lora_filter),
            system_filter=str(system_filter),
        )

        if not self.__class__._cache_entries:
            print("[PromptReplay] No entries available.")
            return ("", "no_entries")

        # "idx | ..." -> idx
        m = re.match(r"^\s*(\d+)\s*\|", str(pick))
        if not m:
            print("[PromptReplay] Could not parse selection index.")
            return ("", "bad_selection")

        idx = int(m.group(1))
        if idx < 0 or idx >= len(self.__class__._cache_entries):
            print("[PromptReplay] Selection index out of range.")
            return ("", "out_of_range")

        e = self.__class__._cache_entries[idx]
        prompt = e.get("final_prompt", "") or ""

        meta = {
            "timestamp": e.get("timestamp"),
            "json_world": e.get("json_world"),
            "system_prompt": e.get("system_prompt"),
            "gender": e.get("gender"),
            "custom_intro": e.get("custom_intro"),
            "lora_triggers": e.get("lora_triggers"),
            "source": e.get("source"),
            "node_version": e.get("node_version"),
        }

        print(f"[PromptReplay] Replayed: {meta.get('timestamp')} | {meta.get('json_world')} | {meta.get('source')}")
        return (prompt, json.dumps(meta, ensure_ascii=False))
