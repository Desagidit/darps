# DARPS Architecture

How the engine works, module by module. For *why* it works this way, read
DECISIONS.md. For the pack format contract, read SPEC.md.

## The one-sentence architecture

DARPS is a conversation layer between a host game and an LLM: per call the
host names who is addressed (or what is examined) and hands over a small world
snapshot; the engine assembles a scoped, condition-gated context, lets the
model speak, then validates every event it proposes before anything touches
narrative state.

## What DARPS is NOT

Not a game engine. It moves no items, tracks no quests, completes no goals,
and never guesses who the player is talking to. The host owns the world and
signals progress with **flags**; DARPS owns only the narrative it is the
authority on — what characters know/hide, what the player has learned,
attitudes, canon, conversation history.

## Call pipeline (orchestrator.py)

```
host: talk(character, message, world?, tone?) | examine(target, message, world?, tone?)
   │
   ▼
[1] EFFECTIVE VIEW — narrative memory + the host's snapshot for THIS call:
    location, present characters, accessible items, flags
    (world.flags merged over the optional flags_file, re-read every call)
   │
   ▼
[2] CLASSIFIER (cheap model, temperature 0) — screening, NEVER routing
    duties: guardrails (meta/injection → manifest meta_response, no character
    call), tone (skipped if host supplies it), topic keywords,
    physics violations. Opt-in (`mention_resolver: true`): fuzzy entity-
    mention resolution — the prompt gains a roster of ids/names/aliases
    (display strings; still zero secrets) and reports loosely-spelled
    references; ids are validated and can only ADD to deterministic matching.
    Config `guardrails: false` + host tone + resolver off = zero screening calls.
   â”‚
   â–¼
[2Â½] SENTIMENT (talk + tracks only; cheap model) â€” player message + tone +
     recent player messages + already-found evidence + layered secret-free
     guidance (pack baseline plus character supplement) for every declared
     attitude. Proposes one coarse -2..2 shift per track;
     the engine strips unknown ids, clamps and speed-scales each, then projects
     all fractional values for this turn. It never sees hidden character
     knowledge, ground-truth vars, or the generated reply.
   â”‚
   â–¼
[2Â¾] PERSONA (when declared; talk + examine; cheap model) â€” established
     player role + pack-authored session-level criteria + recent player inputs.
     Validated, speed-scaled values are persisted once per session, never per
     character, and never enter response-generation prompts.
   │
   ├── talk ────► [3a] CHARACTER: world bible + own knowledge (when-gated) +
   │             SHARED_KNOWLEDGE entries of this turn's RELEVANT entities (addressee ∪
   │             host-declared scene ∪ deterministic name/alias mentions in
   │             the message), scope-filtered by the speaker's `knowledge_scopes:` —
   │             bounded retrieval: an irrelevant entity's lore never enters
   │             context + track prose (not numbers) + canon + journal +
   │             history + scene objects + tone. The same assembly yields the
   │             REVEALABLE set — the only facts this character may reveal
   │             THIS TURN.
   └── examine ─► [3b] NARRATOR: world bible + location doc (+ examined item's
                 ground-truth description) + canon + journal + discovery
                 instruction (engine pre-authorizes search_reveals by trigger match
                 + item examine_reveals by alias resolution, both gate-checked)
   │
   ▼
[4] VALIDATION (validate.py) — the gate
    events block parsed; reveals checked against fact gates (requires +
    conditions via conditions.py), canon_additions capped (or discarded when
    config `canon: false`),
    story_relevance clamped w/ safe default. Narrator reveals must be in the
    pre-authorized set. Failures are stripped, not errors — prose displays,
    state stays clean, discrepancy visible in logs.
   │
   ▼
[5] APPLY + PACING → result dict
    tracks updated (unless config tracks: false); reveals → journal + canon;
    canon_additions → canon when enabled (improvise once, canon forever); history trimmed;
    fruitless-turn counter ticks on story_relevance≥1 without a reveal, freezes on 0,
    resets on any reveal. Deltas computed for the host to mirror.
```

## The result dict (the client boundary)

`{"speaker", "prose", "tone", "deltas"}` where `deltas` =
`{"tracks", "persona", "facts_learned", "canon_added"}` — what changed in DARPS's
narrative memory this call. Anything that can render this is a DARPS client:
the HTTP server, the CLI dev harness, a GUI later. Keep this boundary clean.
`tracks` is `{track_id: {character_id: new_value}}`.

## The HTTP server

`darps serve <pack>` (`server.py`, stdlib `http.server` — no new deps) wraps
the two calls as JSON over `localhost`, so a non-Python host (Unity, Unreal, a
browser) drives DARPS as a sidecar:

```
GET  /health                       -> {"status","pack"}
GET  /pack                         -> safe integration metadata
POST /session   {state?,session?}  -> {"session","state"}    new or restored
GET  /state?session=ID             -> {"session","state"}
GET  /tracks?session=ID            -> {"session","tracks"}
GET  /journal?session=ID           -> learned journal entries
GET  /persona?session=ID           -> {"session","persona"}
POST /state     {session,state}    -> {"session","state"}    restore a save
POST /session/close {session}      -> {"closed"}
POST /talk      {session,character,message,world?,tone?} -> result dict
POST /talk/stream  same body -> Server-Sent Events     prose chunks, then
                   event: done carrying the result dict
POST /examine   {session,target,message?,world?,tone?} -> result dict
POST /examine/stream same body -> Server-Sent Events, same truth boundary
POST /adjust_track {session,character,change?|value?,track?} host-driven track change, no LLM
POST /grant_fact {session,fact}                        host-granted fact, no LLM
POST /add_canon {session,text}                         host-authored canon, no LLM
```

Streaming (`talk_stream` and `examine_stream`, library or HTTP): only prose streams — an
incremental fence detector withholds the events block (a small tail is held
back so a partial fence never leaks) — and `deltas` arrive only
with the final `done` frame, after the complete reply passes the gate. Same
assembly, same gate, same state writes as the blocking call; the split into
`_prepare_talk`/`_apply_talk` is shared verbatim so the two paths cannot
drift. Each streaming path shares its preparation/application functions with
its blocking twin. `llm.call_stream` logs the full prompt/response to calls.jsonl once
the stream ends (`"streamed": true`).

Sessions are in-memory, serialized by a per-session lock; the server does
**not** autosave, so **persistence is the host's job** via `/state` — store
the versioned, pack-bound blob, restore it with `POST /session {state}`. State
is normalized before installation: wrong identity and unknown ids are rejected,
missing narrative fields default, and track/persona values clamp. HTTP failures
use structured error objects; provider failures return 502, and failures after
SSE headers arrive as an `error` event. A reference C# client lives in
[clients/DarpsClient.cs](../clients/DarpsClient.cs).

## Module responsibilities

| Module | Owns | Must never |
|---|---|---|
| `orchestrator.py` | call pipeline, context assembly, pacing | contain pack-specific content; guess a target |
| `validate.py` | runtime event gate | let an unvalidated field touch state |
| `conditions.py` | the closed gate vocabulary | grow without SPEC+lint in same commit |
| `content.py` | pack layout, prompt layering, knowledge rendering | leak `when`-false knowledge |
| `lint.py` | static pack validation, reachability | drift from runtime semantics |
| `llm.py` | provider HTTP (stdlib), call logging, events parsing | require heavy deps |
| `state.py` | narrative-memory shape, save/load, session persona | store world state (the host owns it) |
| `scaffold.py` | `darps new` template | emit a pack that fails lint |
| `server.py` | localhost HTTP layer, session registry | own persistence or the world |

## Knowledge layers

What a character knows is assembled from, broadest to narrowest:
1. `world.md` — universal (every context, narrator included)
2. `shared_knowledge:` entries — entity-centric shared lore: each entity file
   (character/item/location) declares what others know ABOUT it, by scope
   (`common` implicit for all; named scopes held via `knowledge_scopes:`). Pulled only
   for entities RELEVANT to the turn — addressee, host-declared scene, and
   deterministic name/alias mentions in the message. Bounded retrieval by
   subject: no relevance, no lore, no cross-contamination.
3. character file `knowledge:` — individual (always in, when-gated)
4. canon + journal — emergent: improvised `canon_additions` and found facts
In `shared_knowledge[].when`, `self` binds to the SUBJECT entity (the file owner).
Testimony authority is **derived** from this assembly: a character may reveal
fact F only if their briefing holds a revealing entry for F this turn (there
is no `revealed_by` field) — so context and reveal authority cannot disagree.

## Secrecy model

Three nested layers, strongest first:
1. **Context isolation** — `when`-gated (or unsubscribed-scope) knowledge is
   evaluated at prompt assembly; a false gate means the text never exists in
   that context. Innocent characters cannot leak what they were never told.
2. **Runtime gate** — even in-context revealable knowledge only enters the
   journal when the linked fact's gates pass validation, and only via a
   character whose briefing reveals it.
3. **Prompt instruction** — disclosure policies (`why`, `tell`) shape *how*
   characters conceal. Weakest layer; never the only one for anything secret.

## Flags: the host's progress signal

The host tells DARPS how the story has advanced by setting flags — injected
per call (`world.flags`) and/or written to a YAML the game keeps up to date
(config `flags_file`, re-read every call; per-call flags win). Pack knowledge
gates on them with `when:` — including negations for lies that expire
(`{not: {flag: clue_c}}`). Flag names are never linted: they belong to the
host, so the validator treats them as satisfiable-in-principle when proving
fact reachability.

## Items: description, not simulation

An item file is ground truth for narration plus optional gated
`examine_reveals`. The host declares per call which items are in the scene
(`world.accessible_items`); only those can be examined, and prompts
instruct models not to assert objects the scene doesn't establish. If the
host declares no scene, item narration stays non-committal. Aliases +
triggers resolve loose nouns ("the snifter") deterministically.

## Pacing model (simplified)

`fruitless_turns` counts engaged-but-fruitless calls (self-reported story_relevance,
clamped, default 1). The HOST's config sets one threshold and one style
(`hints: {after_turns: N, style: subtle|pointed|forthcoming}`); entities opt out
with `hints: false`. Hints are targeted: the engine picks a currently
reachable fact and aims the nudge (character tell / narration lingering on a
findable's `where`). `forthcoming` additionally evaluates `track_gte` gates
with slack 1 — the only place hints change rules, and it's an engine decision.

## Attitude model

Tracks are engine-held, potentially fractional numbers; characters perform
author-written `track_prose` thresholds, never numbers. A separate secret-free
attitude call judges every declared track independently from pack-wide
baseline plus any character-specific supplement. The engine speed-scales each coarse shift and uses all projected
values for the current reply and reveal gates. The host can disable the whole mechanic
(`tracks: false`): shifts are ignored, prose reads neutral, and `track_gte`
gates evaluate true (the mechanic is off; content must not lock forever).

## Persona model

Persona is player-centric and session-scoped, deliberately separate from
character attitude tracks. Optional manifest dimensions define bounds,
default, speed, and required guidance. A secret-free classifier judges every
talk and examine input, using recent player inputs only to recognize sustained
consistency or repetition. Validated values persist in `state.persona` and are
available through `GET /persona`; neither scores nor criteria enter character
or narrator prompts.

## Provider layer

`config.yaml` (host-owned, not pack-owned): provider preset + model names +
behavior toggles (`tracks`, `canon`, `hints`, `guardrails`, `mention_resolver`,
`flags_file`, `history_turns`, `persona_history_turns`). Presets:
openai/anthropic/ollama/lmstudio/openai_compatible (stdlib HTTP client) +
optional litellm. Keys from `.env` via `darps/env.py`. Two model slots:
`model` (dialogue/narration) and `classifier_model` (cheap classification; a
small local model is fine).

## Observability

`logs/calls.jsonl`: one line per LLM call — tag (`classifier`,
`character:<id>`, `narrator`), model, latency, full prompt, full response.
This is the primary debugging artifact; read it before theorizing.
