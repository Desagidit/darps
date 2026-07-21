---
paths:
  - "darps/**/*.py"
---

# Engine code rules

- Consult the engine-dev skill before nontrivial changes here; it carries the
  same-commit obligations table (conditions vocabulary -> SPEC.md §6 + lint.py;
  events fields -> validate.py twin + template + SPEC §10; schema -> lint +
  scaffold + SPEC).
- No pack-specific content in this package — if a string mentions detectives,
  manors, or any one game, it belongs in a pack or is a bug.
- Model-supplied data reaches state only through validate.py with a safe
  default for omission.
- Never add a hard dependency beyond pyyaml; providers use the stdlib HTTP
  client in llm.py.
- Any change to prompt assembly gets checked for context leaks: `when`-false
  knowledge and vars.yaml must remain unreachable from LLM contexts.
- Behavior changes require a stub-test group in tests/smoke.py (stub
  darps.llm.call; no network, no keys).
