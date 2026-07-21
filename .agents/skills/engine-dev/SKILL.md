---
name: engine-dev
description: Modify the DARPS engine — anything under darps/ (orchestrator, validation, conditions vocabulary, lint, content loader, providers, default prompts, CLI, scaffold) or SPEC.md. Use this for ANY engine code change, new mechanic, new condition type, new events field, new track/goal semantics, provider work, or spec revision — even small "quick fixes" — because engine changes carry same-commit obligations (spec + lint + tests) that are easy to miss.
---

# DARPS engine development

The engine's job is to be boring, small, and general. Its value is the set
of guarantees it keeps: validated events, provable pack solvability, context
isolation, zero heavy dependencies. Every change is judged against those
guarantees first, features second.

## Before writing code, route the change

- Benefits one game → pack field, not engine code. Stop; use pack-authoring.
- Benefits all packs but is prose/behavioral → default prompt template in
  `darps/prompts/`. Prompt-template changes still get a stub test asserting
  the new instruction/data appears in assembled prompts.
- Changes rules/state/gating → engine code, with the obligations below.
- Read `docs/DECISIONS.md` before proposing redesigns — most "why is it
  like this" questions are answered there, and changes should argue with
  the recorded rationale.

## Same-commit obligations (non-negotiable)

| If you touch | You must also update, in the same change |
|---|---|
| `conditions.py` vocabulary | SPEC.md §6 table + `lint.py` (_lint_condition AND reachability semantics) + smoke tests |
| events block fields | `validate.py` twin (clamp/filter/default) + the prompt template schema + SPEC.md §10 + smoke tests |
| pack schema (any file format) | SPEC.md section + `lint.py` checks + `scaffold.py` template (scaffold output must always lint clean) + reference pack if applicable |
| state shape | `state.py` new_state + graceful handling of old saves (use .get with defaults) |
| result dict | SPEC.md §13 + every client (cli.py dev harness, server.py, clients/DarpsClient.cs) |

The linter must never drift from runtime semantics: `lint.py`'s
best-case evaluation and `validate.py`'s runtime evaluation are two views of
the same rules.

## Design rules that govern implementations

- **LLM proposes, engine disposes.** New model-supplied data enters state
  only through a validate.py filter with a safe default for omission.
  Fail open on sloppiness (missing field → sensible default), closed on
  secrets (unauthorized reveal → stripped silently).
- **Deterministic layer for critical behavior.** If a behavior must hold
  (reveals, discovery authorization), the LLM classifies and the engine
  decides — never trust model judgment alone for it.
- **No context leaks.** Any change to prompt assembly (content.py,
  orchestrator prompt building) gets reviewed for what can now reach which
  context. `when`-false knowledge and vars.yaml must be unreachable.
- **Stdlib providers.** New provider support extends the presets/adapters in
  llm.py; hard dependencies beyond pyyaml need extraordinary justification.
- **Prompt templates are contracts.** A rule in a template must be
  accompanied by the data needed to apply it (the sticky-targeting bug was
  exactly this violation).

## Testing discipline

- `python tests/smoke.py` — must pass before and after. Every behavior
  change adds a numbered group.
- Pattern: stub the model (`darps.llm.call = fake`), script exact
  classifier/character/narrator JSON replies, drive `Game.talk`/`Game.examine`, assert on
  state and on assembled prompt contents (PROMPTS list). Stub
  `state_mod.save` to avoid writing files. No network, no keys, ever.
- Test the gate, not just the happy path: hallucinated reveal stripped,
  threshold blocks then unlocks, omitted field defaults, old-save keys.
- Lint changes: verify both directions — clean pack passes AND a
  deliberately broken copy produces the new error message.
- After engine changes run `python -m darps validate packs/ashworth-manor`
  and `darps new` → validate the scaffold output.

## Versioning

Breaking pack-format changes bump `darps_spec` in SPEC.md; the engine
declares supported versions in lint.py's manifest check and refuses others
honestly. Additive optional fields are not breaking.
