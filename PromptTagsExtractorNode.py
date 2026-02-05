import re
from collections import Counter


class PromptTagsExtractorNode:
    """
    PFN Prompt -> Tags Extractor
    Estrae parole chiave dal prompt finale per uso gallery / uploader.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "top_k": ("INT", {"default": 30, "min": 5, "max": 80}),
            },
            "optional": {
                # whitelist manuale, es: "nun, veil, latex, ritual"
                "keep_csv": ("STRING", {"default": ""}),
                "min_len": ("INT", {"default": 4, "min": 3, "max": 12}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("tags_csv", "tags_space")
    FUNCTION = "run"
    CATEGORY = "PFN/utils"

    # -------------------------
    # Config base (tradizionale)
    # -------------------------

    _STOPWORDS = set("""
    a an the and or but if then else with without of in on at to for from by as is are was were be been being
    this that these those into over under near between among lora her face lora his faces woman girl man model character person wearing
    looking shown standing sitting posed figure body skin eyes lips hair their yet
    """.split())

    _PROMPT_GARBAGE = set("""
    masterpiece best quality amazing 4k ultra detailed absurdres newest scenery depth field volumetric lighting
    high resolution aesthetic cinematic detailed ultra highres sharp focus 
    """.split())

    # -------------------------
    # Helpers
    # -------------------------

    def _clean_prompt(self, text: str) -> str:
        # rimuove {{TOKENS}}
        text = re.sub(r"\{\{.*?\}\}", " ", text)
        # normalizza trattini
        text = text.replace("—", " ").replace("-", " ")
        # lascia solo alfanumerico
        text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip().lower()
        return text

    def _extract_tags(self, prompt: str, top_k: int, min_len: int, keep_csv: str):
        keep_set = set(
            w.strip().lower()
            for w in keep_csv.split(",")
            if w.strip()
        )

        text = self._clean_prompt(prompt)
        words = []

        for w in text.split():
            if len(w) < min_len:
                continue
            if w in self._STOPWORDS:
                continue
            if w in self._PROMPT_GARBAGE:
                continue
            words.append(w)

        counts = Counter(words)

        scored = []
        for w, c in counts.items():
            bonus = 3 if w in keep_set else 0
            scored.append((c + bonus, w))

        scored.sort(reverse=True)
        return [w for _, w in scored[:top_k]]

    # -------------------------
    # Nodo
    # -------------------------

    def run(self, prompt, top_k, keep_csv="", min_len=4):
        tags = self._extract_tags(prompt, top_k, min_len, keep_csv)
        tags_csv = ", ".join(tags)
        tags_space = " ".join(tags)
        return (tags_csv, tags_space)
