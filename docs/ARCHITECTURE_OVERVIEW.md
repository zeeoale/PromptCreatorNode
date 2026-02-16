
---

# 📄 3️⃣ `docs/ARCHITECTURE_OVERVIEW.md`

```markdown
# PCN Studio — Architecture Overview

## Livelli

### 1. Data Layer

- World JSON
- Pack JSON
- Global JSON (lighting, camera, ecc.)

Output: PCN_CONTEXT.pool

---

### 2. Selection Layer

Nodi modulari:

- World Loader
- Outfit Picker
- Pose Picker
- Background Picker
- Lighting Picker
- Object Picker
- Accessories Picker

Ogni nodo:
- legge PCN_CONTEXT
- modifica selected.*
- passa avanti il contesto

---

### 3. Composition Layer

Prompt Composer:

- Legge world + selected
- Applica regole
- Costruisce prompt_base
- Scrive output.*

---

### 4. LLM Layer

Enhancer separato:

- Temperature
- Top_p
- Repetition penalty
- Model selection

Non modifica world.
Non modifica pool.

Lavora solo su prompt_base.

---

### 5. Render Layer

ComfyUI pipeline esistente:

- KSampler
- LoRA
- Upscale
- Post-processing

PCN Studio non modifica questo livello.

---

## Flusso Dati

World/Pack → PCN_CONTEXT → Picker → Composer → LLM → Render

---

## Design Goals

- Modularità
- Riproducibilità
- Estendibilità futura
- Compatibilità con Classic
- Leggibilità del workflow

PCN Studio deve crescere senza diventare ingestibile.
