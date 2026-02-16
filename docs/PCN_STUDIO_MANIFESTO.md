# PCN Studio — Manifesto

## Visione

PCN Studio nasce per trasformare il PromptCreatorNode da generatore di prompt
a sistema di direzione creativa strutturato.

L'obiettivo non è aumentare la casualità.
L'obiettivo è disciplinarla.

PCN Studio introduce stratificazione, modularità e controllo,
senza rompere la stabilità della versione Classic.

---

## Principi Fondanti

### 1. Separazione dei Livelli

PCN Studio è diviso in layer indipendenti:

- Data Layer (World + Pack)
- Selection Layer (Picker)
- Composition Layer (Composer)
- LLM Layer (Enhancer)
- Render Layer (Comfy pipeline)

Ogni layer ha responsabilità precise.
Nessun layer deve fare il lavoro di un altro.

---

### 2. Backward Compatibility

PromptCreatorNode Classic resta stabile.
PCN Studio non rompe i world esistenti.
Ogni evoluzione deve essere opzionale.

---

### 3. PCN_CONTEXT come Contratto Universale

Tutti i nodi della Suite comunicano tramite un unico oggetto:
PCN_CONTEXT.

Nessun nodo deve:
- ricaricare file
- generare stato nascosto
- dipendere da logiche interne non visibili

---

### 4. Modularità > Monolite

Funzioni complesse devono vivere in nodi separati.
UI pesanti devono essere evitate.
Il canvas può crescere, ma l’architettura deve restare leggibile.

---

### 5. Direzione > RNG

La casualità è uno strumento.
La coerenza è un obiettivo.

PCN Studio permette:
- Lock per categoria
- Weighted selection
- Stickiness (coerenza tra run)
- Reproducibilità completa

---

## Obiettivo 2.0

Creare un ecosistema:

- PCN Classic (Stable)
- PCN Studio (Advanced)
- Pack Format (estensibile)
- World Manifest modulare

PCN Studio non è un refactor.
È una maturazione architetturale.
