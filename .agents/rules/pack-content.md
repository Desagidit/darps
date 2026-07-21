---
paths:
  - "packs/**"
---

# Pack content rules

- Packs are declarative YAML only — no code, no schema fields not in SPEC.md.
- Run `python -m darps validate <pack>` after every edit round; errors block,
  warnings are usually real mistakes.
- vars.yaml is the one spoiler file; it must act only through `when` gates
  and goal targets.
- New mechanics needed by content are engine feature requests (engine-dev
  skill), never pack hacks.
