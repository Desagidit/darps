# DARPS — Dynamic Agentic Roleplaying System

A conversation layer between a host game and an LLM. The host says who is
addressed, where, and what the player said; DARPS assembles gated context,
calls the LLM, validates every proposed event, and returns prose + narrative
deltas. **The engine owns the narrative truth; LLMs only narrate.** The host
game owns the world (items, location, progress flags) and injects it per
call. Game content is a declarative "pack".

## Commands

- Serve (the real interface): `python -m darps serve packs/ashworth-manor`
- Dev harness (drive the API by hand): `python -m darps play packs/ashworth-manor`
  (`@butler <msg>` talk, `x <target> [msg]` examine, `/flag <name>` toggle)
- Validate a pack: `python -m darps validate <pack>`  (static solvability lint)
- Scaffold a pack: `python -m darps new <dir>`
- Tests: `python tests/smoke.py`  (full loop, stubbed LLM — no key needed)
- Install: `pip install -r requirements.txt` (just pyyaml; providers use stdlib HTTP)

## Map

- `darps/` — engine package. `orchestrator.py` (call pipeline: talk/examine),
  `validate.py` (runtime gate), `conditions.py` (closed condition vocabulary),
  `lint.py` (static validator), `content.py` (pack loader), `server.py`
  (localhost HTTP layer + session registry), `llm.py` (providers + call log),
  `prompts/` (default templates), `scaffold.py`, `cli.py`
- `packs/ashworth-manor/` — reference pack (1923 murder mystery)
- `clients/` — reference host clients (C# for Unity); document the wire
  contract, not compiled or tested here
- `SPEC.md` — the pack format + API contract, versioned. This is the product.
- `docs/ARCHITECTURE.md` — how a call works, module by module
- `docs/DECISIONS.md` — design rationale. **Read before proposing redesigns.**
- `docs/GUIDE.md` — human-facing explainer. **Don't read it for context** —
  it's ARCHITECTURE.md's content in longer prose for newcomers, so loading it
  costs tokens and adds nothing. Do keep it accurate: when engine behavior
  changes in a way a host developer or pack author would notice, update it
  (§3 call walkthrough, §4 secrecy, §5 consequences, §6 hints, §7 objects,
  §10 practical matters).
- `logs/calls.jsonl` — every LLM call: full prompt, response, tag, latency

## Invariants (violating these is a bug, not a style choice)

1. **Engine/content boundary.** If a feature can be a pack field instead of
   engine code, it becomes a pack field. Nothing Ashworth-specific in `darps/`.
2. **Closed condition vocabulary.** Gates use only the types in
   `conditions.py`. Growing the vocabulary requires updating `conditions.py`,
   SPEC.md §6, AND `lint.py` in the same commit. Never accept arbitrary
   expressions or code in packs.
3. **LLM proposes, engine disposes.** No LLM output touches state except
   through `validate.py`. New event fields need a validation twin.
4. **Context isolation is the secrecy mechanism.** Ground truth (`vars.yaml`)
   and `when`-gated knowledge must never reach a context whose gate is false.
   When editing prompt assembly, check what leaks.
5. **Fail open on model sloppiness, closed on secrets.** A model omitting an
   events field degrades gracefully (defaults); a model inventing a reveal
   gets stripped. Negation (`not:`) must never turn malformed into true.
6. **Numbers stay in the engine.** LLM contexts see disposition *prose*
   (`track_prose`), never raw track values.
7. **The host owns the world; DARPS owns the narrative.** Persist only
   facts_learned/tracks/canon/conversations/fruitless_turns. Never store or move items,
   locations, or flags — they arrive per call (world snapshot / flags_file)
   and behavior knobs (tracks, hints, guardrails) are host config, not pack
   content. DARPS never guesses who is being addressed.

## Working style

- Debugging misbehavior: read `logs/calls.jsonl` FIRST. Classify: prompt-
  contract failure (rule without data, missing prohibition) vs engine failure.
  Most bugs are prompt-contract. See the `playtest-debug` skill.
- Fixes are layered: pack data → prompt template → deterministic engine
  override. Critical behaviors (reveals, discovery authorization) get the
  engine layer.
- Every behavior fix lands with a stub-test group in `tests/smoke.py`.
  Tests stub `darps.llm.call` — never require an API key or network.
- Prompt templates are contracts: if a template asks the model to apply a
  rule, the prompt must contain the data the rule needs.
- Generalizing engine fixes: if a fix helps all packs, it goes in
  `darps/prompts/` defaults, not a pack override.
- Keep saves/ and logs/ out of commits (gitignored).
