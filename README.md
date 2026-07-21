# DARPS — Dynamic Agentic Roleplaying System

A **conversation layer between a host game and an LLM**. Your game says
*"the player is talking to this character, here, and said this"*; DARPS does the
heavy lifting — context assembly, secrecy, guardrails, attitudes, validation
— and returns in-character prose plus what changed. The characters and their
secrets are **content**: a "pack" of declarative YAML anyone can write,
validate, and share. The engine owns the narrative truth; LLMs only narrate,
and everything they propose is validated before it counts.

- **SPEC.md** — the pack format and API contract. The actual product; written
  so a second engine could be built against it.
- **darps/** — the reference engine (Python, one dependency).
- **packs/ashworth-manor/** — the reference pack: a 1923 country-house murder.
- **docs/** — the MkDocs Material developer site: onboarding, authoring,
  integration, API reference, recipes, and engine internals.
- **clients/** — reference host clients (C# for Unity).
- **CLAUDE.md + .claude/** — agentic-development setup: project contract,
  path-gated rules, and skills for pack authoring, engine work, and playtest
  debugging (works with Claude Code out of the box).

## Quick start

```bash
pip install -r requirements.txt      # just pyyaml
cp .env.example .env                 # add your API key (or use a local model)
python -m darps serve packs/ashworth-manor    # HTTP layer for your game
python -m darps play  packs/ashworth-manor    # or: dev harness, talk by hand
```

In the dev harness you play your game's role: `@butler what did you hear?`,
`x desk search the drawers`, `/flag cabinet_open` to toggle a progress flag.

Providers: set `provider:` in config.yaml to `anthropic`, `openai`, `ollama`,
`lmstudio`, `openai_compatible` (any OpenAI-style server), or `litellm`
(optional dep). Local models need no key.

## Wire it to a game

```
POST /talk    {"session": s, "character": "butler", "message": "...",
               "world": {"location": "study", "present": [...],
                         "carried": [...], "flags": {"cabinet_open": true}}}
POST /examine {"session": s, "target": "snifter", "message": "..."}
```

Your game owns the world — location, presence, items, progress flags —
and injects it per call. DARPS owns the narrative: what characters know and
hide, what the player has learned, attitudes, optional improvised canon, history. Responses carry
`deltas` (changed attitude tracks, facts learned, canon) for your game to mirror, and the
session blob round-trips through `/state` so saving stays your game's job.
Optional session-wide player `persona` judgments are kept separate from NPC
attitudes and can be queried through `GET /persona?session=...`.
Full contract in SPEC.md §13–14; a reference C# client is in `clients/`.

## Documentation

```bash
pip install -r requirements-docs.txt
mkdocs serve
mkdocs build --strict
```

The site source lives in `docs/`; `SPEC.md` remains the normative pack and API
contract and is included into the site rather than copied.

## Make your own pack

```bash
python -m darps new packs/my-game    # scaffold a minimal commented pack
$EDITOR packs/my-game/*.yaml
python -m darps validate packs/my-game
python -m darps play packs/my-game
```

`darps validate` statically proves the pack works: every reference resolves,
the fact graph is acyclic, every fact is reachable, every gate satisfiable.
**If it validates, it works.**

## Architecture in one paragraph

Each call: the host names the addressee (never guessed) → a cheap screening
call reads the message only (tone, topics, meta/injection attempts —
deflected before any character context exists) → the character pipeline
assembles a private briefing (sheet + conditionally-included knowledge +
relationship prose + memory) or the narrator pipeline authorizes discoveries
(trigger match + gates) → the LLM's fenced events block is validated against
the fact web → approved events update narrative state → deltas return to the
host. Secrecy is structural: knowledge gated by `when:` conditions never
enters a context at all, so innocent characters cannot leak what they were
never told. Progress lives in host-owned flags; packs gate on them (including
`not:` for lies that expire). See SPEC.md for the full contract.

## Iterating

Content and prompts hot-reload (re-read every call) — edit YAML mid-session.
Every LLM call is logged to `logs/calls.jsonl` with its full prompt and
response. Engine discipline: if a feature can be a pack field instead of
engine code, it becomes a pack field.

## Tests

```bash
python tests/smoke.py    # full loop against the reference pack, stubbed LLM
```
