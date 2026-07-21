---
name: pack-authoring
description: Create, edit, extend, or migrate DARPS game packs — the YAML content that defines characters, facts/clues, locations, items, knowledge, and gating for the conversation layer. Use this whenever the task touches anything under packs/, mentions writing a mystery/scenario/character/clue/location, adding content to a game, balancing difficulty, or making a new game on the engine — even if the user doesn't say "pack". Also use when a pack fails `darps validate` and needs fixing.
---

# Authoring DARPS packs

A pack is the content a host game plugs into the conversation layer:
characters, their knowledge and secrets, facts, places, describable objects.
Everything is declarative YAML validated against SPEC.md — never put code in
a pack, never invent schema fields. If a mechanic seems to need a new field
or condition type, that's an ENGINE change (see the engine-dev skill), not a
pack hack. Verbs, quests, win conditions, and item mechanics belong to the
HOST GAME, not the pack.

## Workflow

1. New pack: `python -m darps new packs/<name>` — scaffolds a minimal valid
   pack with every field commented.
2. Edit YAML. Consult `SPEC.md` for exact schemas (§2 manifest, §4 facts,
   §5 characters/knowledge, §6 conditions, §7 locations, §8 items).
3. `python -m darps validate packs/<name>` after EVERY edit round. Fix
   errors before playing; take warnings seriously (they're usually real
   authoring mistakes like an undisclosed testimony fact).
4. Spot-check with the dev harness: `python -m darps play packs/<name>`
   (needs a provider key in .env) — `@char <msg>` to talk, `x <target>` to
   examine, `/flag <name>` to simulate the host game's progress signals.
   Or extend `tests/smoke.py` with stubbed turns for behavior you must
   guarantee.

## The mental model (get this right and the rest is writing)

- **Facts are the spine.** Every discovery is a fact with gates: `requires`
  (fact prerequisites) + `conditions` (closed vocabulary). A fact needs a
  source: a location's `search_reveals` rule, an item's
  `examine_reveals`, OR a `knowledge`/`shared_knowledge` entry that `reveals:` it — WHO
  can reveal testimony is derived from revealing entries in the briefing;
  there is no revealed_by field. The engine strips any reveal that doesn't
  pass the gate. Its `journal_text` is the exact player-facing entry returned
  with the fact id when learned; use `>-` for multiline journal text.
- **Knowledge entries are what a character's LLM context contains.** Three
  flavors in one list: plain (freely shareable), `reveals: <fact_id>` +
  `why`/`tell` (concealed, linked to the gated fact web), and `when:`-gated
  (only enters context if conditions hold — THE secrecy mechanism; a secret
  protected only by instructions is not protected).
- **Shared knowledge goes in `shared_knowledge:` on the entity it describes**, not
  copy-paste and not world.md (which also feeds the narrator). The gun
  cabinet's file says what people know about the cabinet; Lady Ashworth's
  file says what people know about her. Entries have the knowledge shape
  (content/when/reveals); `scope:` defaults to `common` (everyone), named
  scopes reach characters with `knowledge_scopes: [scope]`. In
  `shared_knowledge[].when`, `self` =
  the SUBJECT entity. About entries enter a briefing only when the subject is
  RELEVANT (addressee, scene, or mentioned by name/alias) — so alias lists
  matter doubly: they also drive mention-relevance.
- **Host flags are the progress signal.** The game injects flags per call
  (or keeps a flags file up to date); knowledge and examine_reveals gate on
  them — `{flag: clue_a}` activates a confession, `{not: {flag: clue_c}}`
  keeps a lie in context *until* the game signals otherwise. Flag names are
  a contract with the host game, not lintable — document them in comments.
- **Ground truth lives in vars.yaml** and acts only through `when` gates.
  One character file serves every variant of who-did-it.
- **Tracks are performed, not shown.** Define each track's shared,
  secret-free adjudication `guidance` beside its bounds in `pack.yaml`. Give
  each character `track_settings` with an authored `start` and positive
  `speed`; add character guidance only as a supplement for exceptions or
  special sensitivities. Then write `track_prose`
  bands for the reachable fractional range; characters never see numbers.
  Slow speeds make attitudes require sustained conduct rather than one exchange.
  Every declared track is judged independently; keep baseline guidance
  concrete about what raises, lowers, and does not change it.
  (The host can disable
  tracks entirely — don't gate anything mission-critical on track_gte alone
  if the pack should survive `tracks: false`... it will, gates open, but the
  pacing intent is lost.)
- **Persona is player-centric, not an attitude track.** Optional `persona:`
  dimensions in `pack.yaml` define session-wide bounds, default, speed, and
  concrete guidance for judging all talk/examine inputs. Persona never enters
  response prompts; the host queries it for rewards or analytics. Do not put
  NPC feelings in persona or player-performance judgments in tracks.
- **Items are describable entities**, nothing more: name/description ground
  truth, `triggers`/`aliases` for noun matching, optional gated
  `examine_reveals`. The host declares what's in the scene per call; DARPS
  never moves or holds anything.
- **Aliases everywhere.** Characters, items, and locations take `aliases:`
  lists — the names players actually use ("her Ladyship", "the snifter").
- **Hints are a boolean here, a knob there.** An entity that should never
  nudge the player gets `hints: false`; severity and thresholds are host
  config, never pack content.

## Authoring quality checklist (beyond what lint catches)

- Every character has 1–2 paragraphs of general biography — without it the
  LLM invents contradictory life details. (Improvised details do become
  canon automatically, but seeded biography is better than lucky dice.)
- Concealment needs a `tell` — it's what makes hints work and interrogation
  readable.
- The culprit-equivalent's `when`-gated block must specify: how they lie,
  what they deflect toward, and exactly what evidence combination cracks
  them.
- Search-reveal `triggers` and item `triggers`/`aliases` should cover synonyms a player
  would actually type (desk/drawer/papers; railing/banister).
- Solvability floor: testimony-gated facts need a plausible path to the
  track threshold; check the track and character guidance explain how trust
  is earned. Keep a physical-evidence route where possible so alienating one
  character can't softlock the host's story.
- Flag-gated content: write BOTH sides (the lie under `not:`, the truth
  under the flag) or the character goes silent on the topic in one state.
- vars.yaml is the one spoiler file — keep it minimal.

## Reference pack

`packs/ashworth-manor/` is the worked example of every pattern above
(conditional guilty knowledge, disclosure policy with tell, threshold-gated
testimony, flag-gated examine_reveals on the gun cabinet, alias/trigger
design). When unsure how a field is used in practice, read the corresponding
Ashworth file before inventing.
