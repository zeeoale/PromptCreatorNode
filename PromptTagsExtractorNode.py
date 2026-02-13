import re
import os
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
                # ✅ nuovo: nome world/json per includere tag “identitari”
                # esempi:
                # "PFN_Tokyo_Street_Style_HipHop.json"
                # "PFN_Tokyo_Dance_Crew_Studio"
                "json_name": ("STRING", {"default": ""}),
                # se vuoi controllare quanto “forzare” i token del nome
                "force_name_tokens": ("BOOLEAN", {"default": True}),
                "name_tokens_max": ("INT", {"default": 12, "min": 3, "max": 24}),
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

    def _tokenize_json_name(self, json_name: str, min_len: int, max_tokens: int):
        if not json_name:
            return []

        # se arriva un path o un filename, prendiamo solo il basename
        base = os.path.basename(json_name.strip())

        # togli estensione .json se presente
        base = re.sub(r"\.json$", "", base, flags=re.IGNORECASE)

        # normalizza separatori: underscore, dash, spazi
        base = base.replace("-", " ").replace("_", " ")
        base = re.sub(r"\s+", " ", base).strip().lower()

        # tokenizza
        raw = base.split()

        out = []
        for w in raw:
            if len(w) < min_len:
                continue
            # filtra roba troppo “tecnica”
            if w in {"json"}:
                continue
            # se vuoi tenere "pfn" come tag identitario, NON filtrarlo.
            # Se invece non lo vuoi, aggiungilo qui:
            # if w == "pfn": continue

            out.append(w)

        # de-dup preservando ordine
        seen = set()
        uniq = []
        for w in out:
            if w not in seen:
                seen.add(w)
                uniq.append(w)

        return uniq[:max_tokens]

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

    def run(self, prompt, top_k, keep_csv="", min_len=4, json_name="", force_name_tokens=True, name_tokens_max=12):
        base_tags = self._extract_tags(prompt, top_k, min_len, keep_csv)

        name_tokens = self._tokenize_json_name(json_name, min_len=min_len, max_tokens=name_tokens_max)

        if name_tokens:
            if force_name_tokens:
                # ✅ forzali in testa (identità sempre presente)
                tags = name_tokens + [t for t in base_tags if t not in set(name_tokens)]
            else:
                # alternativa: aggiungili solo se non ci sono già
                tags = base_tags[:]
                for t in name_tokens:
                    if t not in tags:
                        tags.append(t)
        else:
            tags = base_tags

        tags_csv = ", ".join(tags)
        tags_space = " ".join(tags)
        return (tags_csv, tags_space)
