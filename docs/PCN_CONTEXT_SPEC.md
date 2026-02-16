# PCN_CONTEXT Specification (v0.1-dev)

## Scopo

PCN_CONTEXT è l’oggetto di stato condiviso tra tutti i nodi della PCN Suite.

Rappresenta l’intero processo creativo in forma serializzabile e riproducibile.

---

## Struttura Base

```json
{
  "version": "PCN_CONTEXT_0.1",
  "world": {},
  "pool": {},
  "selected": {},
  "rules": {},
  "output": {},
  "llm": {},
  "debug": {}
}
