# DARPS Pack Specification — version 6

DARPS (Dynamic Agentic Roleplaying System) is a **conversation layer between a
host game and an LLM**. The host tells DARPS very little per call — who is
being addressed (or what is being examined), where the scene is, the player's
string, and its progress flags — and DARPS does the heavy lifting: guardrails,
alias resolution, gathering the right context slices, calling the LLM, and
validating every proposed event before it touches narrative state.

DARPS does **not** coordinate the game. It moves no items, tracks no quests,
completes no goals. The host owns the world; DARPS owns the narrative it is
the sole authority on: what characters know and hide, what the player has
learned, how characters feel, what has been said.

A game's content is a **pack**: a directory of declarative YAML. This document
is the contract; a second engine could be built against it. Packs declare the
spec version they target (`darps_spec: 6`); engines refuse versions they don't
support. ("Conversation" is meant loosely: talking to a character, but also
examining an item or a place — anything narrated.)

Version 3 standardized every authored fact-source reference on `reveals`:
knowledge entries, entity shared-knowledge entries, location findables, and item
`examine_reveals` entries all use the same key. Versions 1 and 2 are rejected.

Version 4 removes the inert `facts[].found_in` field and renames location
`findables` to `search_reveals`. A physical-search source is now declared once,
on the location rule that contains the trigger and narration guidance.

Version 5 uses “learned” consistently for facts in player state. Fact display
text is `journal_text`; the condition is `fact_learned`; state stores
`facts_learned`; results return structured `{id, journal_text}` additions.

Version 6 removes pre-release relationship aliases and clarifies shared
knowledge: `default_track`, `adjust_track`, `summary`, `shared_knowledge`, and
`knowledge_scopes` replace their ambiguous predecessors. Item `short`,
character `pressure`, reply-side `mood_shift`, and `deltas.disposition` are gone.
Runtime vocabulary is also explicit: classifier model settings and prompt,
plural `attitudes` adjudication, `story_relevance`, `fruitless_turns`, and
`hints.after_turns` replace their narrower or opaque predecessors.

**Design invariant:** every gate in a pack is expressed in the closed
condition vocabulary (§6). No pack contains code. This is what makes packs
safe to download and statically validatable — `darps validate` proves every
fact is reachable before anyone spends a token on it.

## 1. Pack layout

```
my-pack/
├── pack.yaml           # manifest (required)
├── vars.yaml           # ground-truth variables (optional; engine-only)
├── world.md            # tone/setting bible, in every LLM context (required)
├── facts.yaml          # the gated fact web (required)
├── characters/*.yaml   # one file per character (required, ≥1)
├── locations/*.yaml    # one file per location (required, ≥1)
├── items/*.yaml        # describable objects (optional)
├── player.yaml         # who the player is (optional)
└── prompts/*.txt       # optional overrides of engine default templates
```

## 2. pack.yaml — the manifest

```yaml
darps_spec: 6                 # spec version this pack targets
name: Ashworth Manor          # display name; keys the dev harness save file
author: you
player_label: "the detective" # how prompts refer to the player character
start_location: study         # fallback when a call omits world.location

impossible: "leaving the manor before dawn, supernatural acts"
                              # prose the classifier uses to flag
                              # physics-violating input
meta_response: "..."          # canned in-fiction deflection when the
                              # classifier flags meta/injection input

tracks:                       # numeric character-attitude tracks
  disposition:
    min: -3
    max: 3
    default: 0
    guidance: "Kindness raises it; hostility lowers it; routine questions do not."
  fear:
    min: 0
    max: 3
    default: 0
    guidance: "Credible threats raise it; reassurance lowers it."
default_track: disposition    # track used when adjust_track omits one

persona:                      # OPTIONAL session-wide player judgments
  role_consistency:
    min: -3
    max: 3
    default: 0
    speed: 0.25
    guidance: >
      Reward conduct consistent with the established player role. Neutral
      inputs score zero; contradicting the role decreases the value.
```

`persona` is separate from character tracks: each dimension has one value for
the whole session, is judged from both talk and examine inputs, and never
enters character or narrator response prompts. Bounds/default/speed are
numeric, speed is positive, and guidance is required for each dimension.

That is the whole manifest. Intents, goals, item actions, and hint thresholds
were spec-1 concepts: verbs and progress belong to the host game, and pacing
severity is host **config**, not pack content (§13).

## 3. vars.yaml — ground truth

Arbitrary key→value pairs known only to the engine (e.g. `culprit: widow`).
Vars never enter an LLM context directly; they act only through `when`-gated
knowledge (§5). This is where multi-variant scenarios live: change the var,
and the same character files deal out different knowledge.

## 4. facts.yaml — the fact web

A fact is a gated, acquirable piece of ground truth. Learning one adds its id
to `facts_learned` and uses its exact authored `journal_text` in the player's
journal and all future LLM contexts.

```yaml
- id: torn_letter
  requires: []                # fact ids the player must already hold
  journal_text: >-            # authoritative journal entry text
    ...

- id: overheard_quarrel      # testimony: revealed in conversation by whoever
  requires: []                #   holds a knowledge entry revealing it
  conditions:                 # extra gates in the condition vocabulary (§6);
    - {track_gte: {track: disposition, value: 1}}   # `of` defaults to the
  journal_text: >-            # authoritative journal entry text
    ...
```

A fact needs at least one source: a location's `search_reveals` rule (§7), an
item's `examine_reveals` (§8), or a knowledge entry — a
character's own `knowledge:` or any entity's `shared_knowledge:` (§5½) — that
`reveals:` it. **Who can reveal a testimony fact is derived**: a character
may propose it only if their briefing contains a revealing entry *this turn*
(for `shared_knowledge:` entries, that also requires the subject entity to be relevant —
§5½). There is no `revealed_by` field. Facts with no source are unreachable
and fail validation. `requires` must be acyclic.

**The reveal rule (normative):** a fact enters the journal only when the
engine approves it — prerequisites held, conditions true, and (for testimony)
proposed by the right character. LLM proposals that fail any check are
stripped. Engines MUST enforce this; it is the anti-hallucination and
anti-leak guarantee.

## 5. characters/*.yaml

```yaml
id: butler
name: Mr. Halloway
summary: the butler, thirty years in service
aliases: [Halloway, the butler]   # OPTIONAL alternate names (see §12)
hints: true                   # OPTIONAL: false = never delivers pacing hints
knowledge_scopes: [household] # OPTIONAL shared-knowledge scopes held
                              # holds (§5½); `common` is implicit for everyone
shared_knowledge:             # OPTIONAL: what OTHERS know about this entity,
  - content: "..."            # by scope (§5½) — NOT what this character knows
voice: "..."                  # speech style, quirks
background: "..."             # a paragraph of life detail (prevents the LLM
                              # inventing contradictory biography)

track_settings:               # OPTIONAL starting point and sensitivity
  disposition:
    start: -0.5               # defaults to the manifest track default
    speed: 0.5                # positive; coarse shifts are multiplied by this
    guidance: "Protecting the household matters especially to him." # supplement
  fear:
    start: 0
    speed: 0.5
    guidance: "Credible threats raise it; reassurance lowers it."

knowledge:                    # the unified knowledge model
  - content: "He found the body at 11:30 pm."
      # plain entry: known, freely shareable

  - content: "Near ten he heard raised voices..."
    reveals: overheard_quarrel     # links to a fact; carries a policy
    why: "He is protecting her Ladyship."
    tell: "Hesitates a half-second too long."
      # disclosure entry: the character knows it, conceals it, and the
      # linked fact's gates decide when a disclosure is APPROVED

  - content: "There is nothing behind the bookcase — just damp."
    when:                     # inclusion conditions: if false, this entry
      - {not: {flag: door_opened}}   # NEVER enters the LLM context at all
      # conditional entry: context isolation is the secrecy mechanism.
      # This one is a LIE WITH AN EXPIRY: present until the host game
      # sets door_opened. Host flags are the progress signal (§6, §13).

  - content: "YOU KILLED HIM. ..."
    when:
      - {var: culprit, is: self}

track_prose:                  # engine state -> performed attitudes;
  disposition:                # keys are thresholds (highest key ≤ value wins)
    "-2": "Clipped monosyllables..."
    "0":  "Guarded but dutiful..."
    "1":  "Beginning to trust..."
  fear:
    "0": "Steady and unafraid..."
    "1": "Watchful; careful around the player..."
```

Numbers stay in the engine; characters perform the prose. LLM contexts never
see raw track values. Values may be fractional. Omitted `start` uses the
manifest default; omitted `speed` uses `1.0` for backward compatibility.
Track `guidance` in `pack.yaml` defines the shared baseline. Character-level
`guidance` is optional and supplements rather than replaces that baseline;
use it only for exceptions or character-specific sensitivities. Legacy

## 5½. `shared_knowledge:` — what others know about an entity

The middle layer between `world.md` (universal — every context, narrator
included) and a character's own `knowledge:` (individual). Every entity file
— character, item, location — may carry a `shared_knowledge:` list: **what other
characters know about THIS entity, by scope**. It lives on the entity it
describes, so the file a writer has open is where its lore belongs.

```yaml
# items/gun_cabinet.yaml
shared_knowledge:
  - content: "A locked oak gun cabinet stands against the study wall — Sir
      Edmund's. The key went to the constable; the police bring it at dawn."
      # scope omitted -> common: every character knows this about it

# characters/widow.yaml
shared_knowledge:
  - scope: household           # characters declaring this knowledge scope
    content: "The Ashworth marriage went cold years ago; separate rooms."
  - scope: household
    content: "Her sleeping drops went missing this week."
    when: [{var: culprit, is: self}]  # in about entries, `self` = the SUBJECT
    reveals: missing_drops            #   (the entity this file belongs to)
    why: "Nobody wants to say it aloud."   # a SHARED concealed secret: any
    tell: "Eyes flick to her handbag."     #   household character may reveal it
```

Entries have full parity with `knowledge:` entries (`content`, `when:`,
`reveals`/`why`/`tell`). In an about entry's `when:`, `self` binds to the
**subject** — "include this about her iff *she* is the culprit" — as does
`track_gte`'s `of` default.

### Relevance (normative)

About entries enter a speaker's briefing only when the subject entity is
**relevant to the turn**, decided deterministically — no LLM judges what a
character knows:

1. the addressee themselves (shared knowledge renders as their reputation —
   "It is known about you: …"),
2. the scene the host declared: `world.present` characters,
   `carried`/`in_reach` items, the current location,
3. entities the player's message **mentions** — matched against each
   entity's `name`/`aliases` (and item `triggers`),
4. *(opt-in)* entities the **LLM mention resolver** identifies (config
   `mention_resolver: true`): the classifier call receives a roster of
   entity ids/names/aliases (display strings only — it still holds no
   secrets) and may report loosely-spelled or nicknamed references. Resolved
   ids are engine-validated (unknown ids stripped) and can only ADD to the
   deterministic set, never remove from it.

An entity outside this set contributes nothing this turn: retrieval is
bounded by subject, so asking the butler about the weather pulls no Ashworth
gossip into his context. Without the resolver, a nickname the alias list
doesn't cover degrades to "the character doesn't bring it up" — never to a
wrong answer; with it, misspellings and epithets ("the grieving missus")
resolve at the cost of a classifier call every turn.

Scope filtering applies on top: the speaker gets an about entry only if its
`scope` is `common` (the default) or in their `knowledge_scopes` list.

### Authority

The briefing is the reveal authority (§4): a character may reveal a fact
revealed by an about entry only on turns where that entry was actually
pulled — subject relevant, scope held, gates passed. Context and authority
cannot disagree.

Used in `knowledge[].when`, `shared_knowledge[].when` (§5½ — `self` = subject
entity), `facts[].conditions`, and `examine_reveals[].conditions`.

| Condition | True when |
|---|---|
| `{var: <name>, is: <value>}` | ground-truth var equals value; the literal `self` matches the character in context |
| `{fact_learned: <fact_id>}` | the player has learned the fact |
| `{flag: <name>}` | the HOST's flag is set — flags are the game's progress signal, injected per call and/or read from a flags file (§13); packs may gate on any flag name |
| `{track_gte: {track: <t>, value: <n>, of: <char_id>?}}` | the track is ≥ n; `of` defaults to the character in context |
| `{not: <condition>}` | the wrapped condition is false — for knowledge that *expires* (a lie held until a flag is set). Wraps exactly one condition; may not directly wrap another `not`. A malformed inner condition makes the whole `not` false (negation never weakens fail-closed). |

Lists of conditions are conjunctions. Unknown condition types evaluate false
at runtime and are errors at validation time. **Growing this vocabulary
requires updating this table, the evaluator, and the validator in the same
change.** There is deliberately no expression language.

Because flags belong to the host, the validator treats `{flag: ...}` (and its
negation) as satisfiable-in-principle when proving fact reachability; flag
*names* are never statically checkable.

## 7. locations/*.yaml

```yaml
id: study
name: The Study
aliases: [the office]         # OPTIONAL alternate names (see §12)
hints: true                   # OPTIONAL: false = the narrator never hints here
shared_knowledge:             # OPTIONAL: what characters know about this
  - scope: household          #   place, by scope (§5½)
    content: "Sir Edmund took brandy alone here from ten o'clock."
description: "..."            # ground truth for narration in this place
search_reveals:
  - reveals: torn_letter
    where: the desk — its drawers and papers   # used verbatim in hint text
    triggers: [desk, drawer, papers]           # examination keywords that make
                                               # the engine AUTHORIZE discovery
scenery: "..."                # freely improvisable; never yields facts
```

## 8. items/*.yaml — describable entities

An item is **ground truth for narration**, nothing more. DARPS never moves,
holds, or tracks items — the host declares per call which items are in the
scene (`world.carried` / `world.in_reach`, §13), and only those can be
examined or asserted in prose.

```yaml
id: brandy_glass
name: the brandy glass
triggers: [glass, brandy, dregs]   # nouns for deterministic matching
aliases: [snifter]                 # alternate names (see §12)
shared_knowledge: []               # OPTIONAL: what characters KNOW about it,
                                   #   by scope (§5½) — coarser than examining
description: "..."                 # ground truth for examination narration
examine_reveals:                   # examining it may surface facts,
  - reveals: bitter_glass          # through normal §4 gating
    conditions: []                 # optional extra §6 conditions
```

The `{flag: ...}` pattern replaces spec-1 item mechanics: when the host's
world changes (a cabinet gets opened, however the game does that), the host
sets a flag, and gated `examine_reveals`/knowledge respond.

## 9. player.yaml — the protagonist

```yaml
name: The Detective
description: >                # injected into EVERY LLM context: who the
  A retired detective...      # player is — and what they are not
```

What the player carries is the host's business, declared per call.

## 10. The events contract

Character responses end with a fenced ```events``` JSON block:
`reveals` (fact ids proposed for
disclosure), `canon_additions` (when canon building is enabled: ≤3 improvised
biographical or world facts; the engine appends approved ones to global canon
so improvisation becomes consistent),
`story_relevance` (0–2; omitted → 1; drives the fruitless-turn counter).

Attitudes are judged before reply generation in a separate, secret-free
attitude call. It proposes `shifts: {track_id: -2..2}`; the engine strips
unknown tracks, clamps each shift, multiplies it by that character's
`track_settings.<track>.speed`, clamps projected values to their bounds, and
uses every projection for the current reply and gates. Values commit only
after generation completes. The call sees player text, tone, recent player
messages, already-found evidence, and each track's authored `guidance`;
never hidden knowledge, ground-truth vars, or the generated response. For old
overrides must return `shifts`; omitted or malformed maps produce zero changes.

Narrator responses: `reveals` (only ids the engine pre-authorized that turn)
and `story_relevance`.

Engines strip the block from displayed prose and validate every field.

## 11. Prompt overrides

Any of `classifier.txt`, `attitudes.txt`, `persona.txt`, `character.txt`, `narrator.txt` in
`<pack>/prompts/` replaces the engine default. Templates use
`{placeholder}` substitution; `{{` and `}}` escape literal braces. Overrides
MUST preserve the events contract (§10) — the engine parses responses
identically regardless of template origin.

## 12. Aliases

Characters, items, and locations may each carry an optional `aliases:` list of
alternate names — the terms a player is likely to reach for instead of the
canonical `name` ("Lady Ashworth" / "Constance" / "her Ladyship" all mean the
widow; a "desk" may be the item you called a table). Item aliases join
`triggers`/`name`/id in the deterministic matcher that resolves `examine`
targets (longest term wins). Aliases are display strings only — never secret,
never gated, and optional.

## 13. The runtime API

DARPS exposes two response calls. The host supplies the target; DARPS never guesses
one, so cross-reference confusion ("asked *about* X, answered as X") is
structurally impossible.

```python
Game.talk(character_id, message, *, world=None, tone=None) -> result
Game.examine(target, message="", *, world=None, tone=None) -> result
     # target: an item id, or a loose noun resolved via aliases/triggers
```

Three host-authority writes complete the surface — no LLM call, no world
snapshot; they let the game push what happened *outside* conversation into
DARPS's narrative memory:

```python
Game.adjust_track(character_id, *, change=+2 | value=1, track=None)
     # attitude changed by a GAME event (a gift, a rescue). Exactly one of
     # exactly one of change/value; track defaults to default_track; clamped.
     # -> {"deltas":{"tracks":{track:{character_id:new_value}}}}
Game.grant_fact(fact_id)
     # the player learned a fact OUTSIDE conversation (a cutscene, another
     # system). The host is authoritative over its own story beats, so this
     # BYPASSES the fact's gates; the id must exist in the pack. Idempotent.
     # -> {"deltas": {"facts_learned":
     #       [{"id": fact_id, "journal_text": exact authored text}] or []}}
Game.add_canon(text)
     # establish incidental narrative truth from a cutscene/host event.
     # Non-empty, whitespace-normalized, at most 500 characters, idempotent.
     # With canon:false this is a no-op.
     # -> {"deltas":{"canon_added":[text] or []}}
```

### The world snapshot (all keys optional)

```python
world = {"present":  [char_ids],      # who is in the scene
         "location": location_id,     # default: manifest start_location
         "carried":  [item_ids],      # what the player carries
         "in_reach": [item_ids],      # other items in the scene
         "flags":    {name: bool}}    # the host's progress signal
```

Injected per call, used for that turn, **never persisted**. If the host
declares `carried`/`in_reach`, only those items can be examined or asserted;
if it declares neither, item narration stays non-committal. Flags may also be
read from a **flags file** the game keeps up to date (config `flags_file`;
re-read every call; per-call `world.flags` win on conflict).

### The result dict

```python
{"speaker": str|None,       # character name, or None for narration
 "prose": str,
 "tone": str,               # the tone used (host-supplied or classifier-read)
 "deltas": {"tracks": {track_id: {char_id: new_value}},
            "persona": {persona_id: new_value},
            "facts_learned": [{"id": fact_id,
                                "journal_text": exact authored text}],
            "canon_added": [strings]}}
```

`deltas` is what changed in DARPS's narrative memory this turn — the host
mirrors whatever it cares about (a revealed fact might advance a quest).

### Streaming

`Game.talk_stream(...)` and `Game.examine_stream(...)` are streaming twins of
the two response calls, for hosts that want prose to appear as it is generated
instead of after the full reply. They are generators of events:

```python
{"type": "text", "text": "<prose chunk>"}     # zero or more
{"type": "done", "result": <the result dict>} # exactly once, last
```

Normative semantics:
- **Only prose streams.** The model's fenced events block is withheld from
  the text stream (an incremental fence detector holds back a small tail so
  a partial fence can never leak to the player).
- **`deltas` exists only in the `done` event** — it is
  produced by the validation gate, which needs the complete reply. A client
  MUST NOT infer state changes from streamed prose.
- `done.result.prose` is the canonical stripped prose; it normally equals
  the concatenated text chunks, and clients may reconcile against it.
- Same assembly, same gate, same state writes as `talk()` — streaming
  changes when the player sees words, never what becomes true.

### The classifier

A cheap screening call over the *message only* — never targeting. Duties:
guardrails (meta/injection attempts → `meta_response` deflection, the
character context is never invoked), tone (skipped if the host
supplies one), topic keywords, and physics violations (`impossible`).
Config `guardrails: false` disables the screening entirely when the host
supplies `tone` (zero classifier calls).

Talk calls with tracks enabled additionally make a cheap `attitudes:<id>`
classification call. It is separate from screening and reply generation;
`tracks: false` removes it.

If the pack declares `persona`, every talk and examine input additionally gets
a cheap `persona` classification. It sees the established player description,
shared world context, already-found evidence, pack-authored guidance, recent
player inputs, input kind, and tone. It
sees no hidden knowledge and its values never enter response prompts. Unknown
ids are stripped, shifts clamp to -2..2, then dimension speed and bounds apply.

### Host configuration (config.yaml — runtime, not pack)

```yaml
provider: ...                # LLM provider + models (see README)
tracks: true                 # false = attitude mechanic off: tracks ignored,
                             #   neutral prose, track_gte gates open
canon: true                  # false = improvised details are not requested,
                             #   persisted, or supplied to later contexts
hints: {after_turns: 6, style: subtle} # pacing: one fruitless-turn threshold
                             #   (subtle|pointed|forthcoming); absent = off.
                             #   forthcoming relaxes track gates by 1.
guardrails: true             # screen every message via the classifier
mention_resolver: false      # LLM fallback for misspelled/nicknamed entity
                             #   references (adds to deterministic matching;
                             #   forces a classifier call every turn)
flags_file: flags.yaml       # optional: host-maintained progress flags
history_turns: 12            # conversation exchanges remembered per character
persona_history_turns: 12    # recent player inputs used for persona consistency
```

Entities opt out of hints with `hints: false` in their own file; severity and
thresholds are the host's, never the pack's.

### Session state (what DARPS persists)

One JSON blob — identity metadata (`state_version`, `pack_id`, `darps_spec`)
plus narrative memory: `turn`, `facts_learned`, `tracks`, `canon`,
per-character `conversations`, `fruitless_turns`, session-level `persona`, and
`persona_history`. `pack_id` is the normalized pack name. It is the save file;
hosts round-trip it via `/state` or store it themselves. Restore rejects a
different pack/spec/state version and unknown entity ids; missing narrative
fields receive defaults, while restored track/persona numbers are clamped to
their current bounds. With `canon: false`, the
`canon` field remains for save compatibility but is neither read into prompts
nor extended; this also prevents old canon in a loaded save from influencing play.

## 14. The HTTP server

`darps serve <pack>` wraps the API as JSON over `localhost` (stdlib only) so
non-Python hosts integrate over HTTP:

```
GET  /health                      -> {"status","pack"}
GET  /pack                        -> safe ids/names/aliases/bounds/capabilities
POST /session   {state?,session?} -> {"session","state"}   (new or restored)
GET  /state?session=ID            -> {"session","state"}
GET  /tracks?session=ID           -> {"session","tracks"}
GET  /journal?session=ID          -> {"session","journal":[{id,journal_text}]}
GET  /persona?session=ID          -> {"session","persona"}
POST /state     {session,state}   -> {"session","state"}   (restore a save)
POST /session/close {session}     -> {"closed"}
POST /talk      {session,character,message,world?,tone?}    -> result dict
POST /talk/stream  same body -> text/event-stream:
                   data: {"type":"text","text":...}  (prose chunks)
                   event: done + data: <result dict> (final)
POST /examine   {session,target,message?,world?,tone?}      -> result dict
POST /examine/stream same body -> text/event-stream, same contract as talk
POST /adjust_track {session,character,change?|value?,track?} -> track delta
POST /grant_fact {session,fact}                    -> {"deltas":{"facts_learned": [...]}}
POST /add_canon {session,text}                     -> {"deltas":{"canon_added": [...]}}
```

Sessions are in-memory; persistence is the host's job via `/state`. A
reference C# client lives in `clients/DarpsClient.cs`.

`GET /pack` is deliberately allow-listed and secret-safe: it exposes entity
ids/display names/aliases, track and persona numeric definitions, the default
track, and capabilities. It never returns facts, descriptions, variables,
knowledge, prompt guidance, or conditions.

Errors use `{"error":{"code","message","diagnostic_id"?}}`. Malformed
requests and invalid state return 400, unknown sessions/routes return 404,
explicit session-id collisions return 409, provider failures return 502, and
unexpected engine failures return 500. `diagnostic_id` accompanies server-side
failures and is printed with their traceback. Once an SSE response has begun,
failures arrive as `event: error` with the same error object in its data frame.
