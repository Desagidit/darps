# DARPS Design Decisions

The reasoning behind the architecture, recorded so future changes (human or
agent) argue with the *reasons*, not just the code. Format: decision,
rationale, what would change our mind.

## D1. The engine owns the truth; the LLM narrates
LLMs invent clues, contradict timelines, and leak solutions under pressure.
All canonical facts live in engine state; models produce prose plus an events
block that the engine validates. **Reverse only if** models become reliably
incapable of hallucination under adversarial play — i.e., never assume it.

## D2. Context isolation is the secrecy mechanism
Secrets are kept by *never entering* innocent contexts (`when`-gated
knowledge evaluated at prompt assembly), not by instructing models to keep
them. Instructions are the weakest layer and are treated as flavor, not
security. A leak-checking second-pass model was considered and deferred:
isolation + validation covers it; add the pass only if playtests show
culprit-context leaks (the one context that necessarily holds the secret).

## D3. Declarative packs, closed condition vocabulary — no code in packs
The genre-vs-generic debate resolved here: the valuable boundary is not
"detective concepts vs none" but **declarative vs Turing-complete**. Because
gates and goals use a small closed vocabulary (`var/is`, `fact_learned`,
`flag`, `track_gte`), `darps validate` can prove solvability by reachability
before anyone plays — and packs are safe to download. The tax: every
vocabulary addition updates evaluator + SPEC §6 + linter in one commit; when
an author needs an arbitrary expression, the answer is a new named condition
type or "no". A trust-required plugin API may come later; it must never be
the default path.

## D4. `guilty_knowledge` generalized to conditional knowledge
Guilt was not a special kind of knowledge — it was *conditionally included*
knowledge (`when: {var: culprit, is: self}`). Unifying knows/hides/guilty
into one `knowledge` list with optional `when` (inclusion) and `reveals`
(policy) annotations gives multi-variant mysteries from single character
files, mid-game knowledge activation (`when: {fact_learned: ...}`), and story
phases (`when: {flag: ...}`) for free.

## D5. Free text in, intent layer first
Buttons were rejected: free text is the point. A cheap classifier call
classifies input into the pack's intent vocabulary before any character
context sees it — which also means injection attempts are classified `meta`
by a context holding zero secrets. Physics violations (`impossible`) deflect
in-fiction, never with error messages.

## D6. Consequences over guardrails
Hostile play is simulated, not refused: tone classification → track
penalties, witnessed hostility → canon (all characters know) → behavior
change via track prose. Hostility is a costly tactic, not a forbidden verb.
Hard rails only for fiction-breaking impossibilities. Keep a floor under
failure: repair paths / physical-evidence routes must exist so consequence
systems can't softlock (lint may enforce this someday).

## D7. Numbers in the engine, prose in the prompt
Models handle in-prompt numeric stats badly (narrating their own meters).
Tracks drive threshold selection of author-written `track_prose`; contexts
never contain raw values. Disposition is deliberately not shown in any UI
meter — reading people is the gameplay.

Disposition judgment is deliberately separate from reply generation. A reply
model conflated its own guarded or evasive performance with a negative change
in how it felt about the player, then overcorrected toward zero when given a
rubric. A secret-free attitude pass now judges player text independently
against layered attitude guidance: a pack-wide baseline avoids repetition,
while character files supplement only exceptions and sensitivities. Coarse per-track scores are
speed-scaled into fractional engine values and projected into the current
reply. Reconsider only
if reply models reliably separate authored behavior from interpersonal change.

Player-centric judgments are not tracks. Attitude tracks answer how one
character feels and are performed in that character's response. Persona
dimensions answer how consistently the player inhabits an established role;
they are session-wide, updated across talk and examine, queryable by the host,
and deliberately absent from response prompts. Keeping the stores separate
prevents a hidden reward score from muddying the elegant character-attitude
model. Reconsider only if a future persona dimension must directly shape NPC
behavior, in which case the host should probably translate it into a flag or
explicit attitude nudge.

## D8. Pacing = relevance-aware fruitless turns, reply-side signal
Hints exist for players who are *trying* and stuck, not ambling. The
`fruitless_turns` counter ticks only on `story_relevance ≥ 1` turns without a reveal. The signal
is self-reported by the reply model because relevance is a topical judgment
of the exchange (which models do well), NOT self-assessed progress (which
they do badly — everything feels like progress from inside the reply).
Progress itself stays engine-defined: facts entering the journal. Hints
escalate subtle→pointed→forthcoming; only level 3 changes rules (track slack
1), diegetically framed as conscience/relenting.

## D9. Layered fixes; deterministic engine layer for critical behavior
Observed failure taxonomy so far: nearly all bugs are prompt-contract
failures — a rule stated without the data to apply it (sticky targeting), or
a missing prohibition (player ventriloquism) — not engine failures. Fix
order: pack data → prompt template → deterministic engine override. Anything
gameplay-critical (conversation targeting, reveals) gets the engine layer:
the LLM classifies, the engine decides. Every fix lands with a stub-test
group.

## D10. Stdlib providers; heavy deps optional
LiteLLM's dependency tree broke installs for a job that is one HTTP POST.
The OpenAI-compatible endpoint is the de facto standard (OpenAI, Ollama,
LM Studio, vLLM) + one Anthropic adapter = zero required deps beyond pyyaml.
LiteLLM remains opt-in. Local-model support is a design constraint, not an
afterthought: schemas carry concrete rubrics/examples because ~8B models
need them; omitted fields default safe.

## D11. Library boundary now, front ends later
`Game.step(text) → result dict` is the whole client contract. CLI first
(zero UI code exercised the entire architecture for weeks); GUI later renders
the same events; an MCP server exposing step/get_state makes any MCP client
a front end. Nothing may couple engine internals to a front end.

## D12. Authored content over procedural; variants as the middle path
Full proceduralism flattens craft into logically-valid sudoku. The path to
replayability is hand-authored variant solutions over one scenario (vars +
conditional knowledge already support it). Ship one great fixed mystery
first; retrofit variants (the data format allows it) once authoring teaches
us what the clue web needs.

## D13. Improvise once, canon forever
Characters will improvise biography under free-text questioning. Fighting it
loses; recording it wins: `canon_additions` from events append to global canon
and enter all future contexts. Contradiction becomes consistency.

This is a host policy, not a universal requirement. `config.yaml` may set
`canon: false` for authored stories that prefer occasional disposable oddities
to allowing improvisation into narrative truth. In that mode old canon is
withheld, the reply contract does not request `canon_additions`, and validation
discards the field if a model supplies it anyway. The state key remains so
saves can move safely between configurations.

## D14. Saves outside packs
Packs are read-only shareable artifacts; state lives with the player
(`saves/<pack-name>.json` in CWD). Re-downloading a pack never destroys
progress; screenshots of packs never contain spoilers except vars.yaml,
which is documented as the one spoiler file.

## D15. Items: non-fungibility as state, capability as inventory
**(Superseded by D17 — kept for the record.)** In the spec-1 text adventure,
an item was one instance with one holder, engine-moved only; capability was
possession; interactions lived on the instrument as declarative effects;
`has_item` gated knowledge and goals. All of that presumed DARPS was the
world's authority. Once the host game owns the world (D16→D17), engine-held
item state is a desync waiting to happen; what survives is the *narration*
half: items as describable entities with `examine_reveals`, and possession
declared per call by the host.

## D16. DARPS as an embeddable layer; the host owns the world
DARPS is not primarily a text adventure — it is a layer a game engine (Unity,
etc.) embeds so its NPCs can speak through an LLM without the game writing prompt
engineering, secrecy logic, or a validation gate. This reframes three things:

- **The host supplies the addressee.** The old free-text router guessed *who*
  was being spoken to, and that guess was the top observed bug ("asked Halloway
  *about* Lady Ashworth, conversation flipped to Lady Ashworth"). The explicit
  verbs (`talk(character, message, …)`) take the target from the host, so the guess —
  and the failure mode — is unreachable. This is D9 taken to its limit: the
  cleanest "engine decides" is the engine not deciding at all when the host
  already knows. Input classification remains, but target selection does not.
- **The host owns the world; DARPS owns the narrative.** A real game already
  tracks NPC presence, real inventory, location, and world flags; duplicating
  that as authoritative DARPS state would desync. So world facts are *injected
  per call* and never persisted; DARPS persists only what it is the authority on
  — disposition, facts learned, history, canon (D1 unchanged: it still owns
  *narrative* truth). Item moves from `give`/`use` become proposals the host
  commits (`deltas.items_moved`), because inventory is the host's to change.
  **Reconsider if** a host ever wants DARPS to be the inventory authority — the
  `world`-omitted path already is, so both coexist.
- **Transport is a local HTTP server, stdlib only.** Skyrim/Unity can't import
  CPython; the de-facto pattern for local-LLM game bridges is a localhost
  sidecar. `darps serve` uses `http.server` — no new dependency (D10 holds).
  Chosen over stdio (universal, curl-debuggable, language-agnostic) and over an
  in-process embed (cross-language CPython hosting is fragile).

The result dict grew a `deltas` block so a host can mirror narrative changes into
its own systems; it is additive (§12), and the events contract (§10) is
unchanged — deltas are derived from already-validated events, never model-
supplied. **Out of scope, by design of the HTTP contract, not blocked by it:**
thousand-NPC content scaling (pack-per-scene / lazy load), stdio transport,
auth/multi-tenant serving, streaming responses. *(D16's transitional
compromises — item-move proposals, a kept free-text path — were removed by
D17.)*

## D17. The narrowing: DARPS is a conversation layer, nothing else (spec 2)
D16 made DARPS embeddable but kept the text-adventure machinery alongside:
item movement, goals/epilogues, free-text target guessing, a three-threshold
hint ladder. Spec 2 deletes the game-coordinator half outright. DARPS takes
very limited info per call — who is addressed / what is examined, where, the
player's string, the host's flags — and returns validated prose + narrative
deltas. "Conversation" is loose: item inspection and narration count.

- **Two calls only** (`talk`, `examine`). No `step()`, no classifier
  targeting — the bug class D16 made avoidable is now unrepresentable. The
  target routing. The classifier handles guardrails (meta/injection), tone,
  topics, physics — a *screening* of the message, never a routing of it.
- **Progress is a host signal, not engine state.** Goals, item movement, and
  `has_item` are gone. The host signals progress with FLAGS (injected per
  call and/or a flags file it keeps up to date); pack knowledge gates on them
  with the existing `when:` mechanism — *(if clue_a → include confession)*,
  *(if not clue_c → include this lie)*. This required adding `not:` to the
  closed vocabulary — the first negation, wrapped tightly (single condition,
  no double-negation, malformed inners stay false) so it can never weaken
  fail-closed. Flag names are deliberately not lintable: they belong to the
  host, so reachability treats them as satisfiable-in-principle.
- **Severity knobs are host config, never pack content.** Sentiment can be
  switched off (`tracks: false` — gates open rather than lock forever, since
  the *mechanic* is off, not the content). Hints collapse from a ladder to
  one threshold + one style in config; entities opt out with a boolean.
  Content says *what*; the host says *how much*.
- **Items became pure description**: ground truth for narration when the host
  says they're in the scene, plus gated `examine_reveals`. What D15 solved
  with engine-moved holders ("no conjuring") is now solved by the scene
  contract: prompts only assert objects the host declared.

What DARPS still owns is exactly its value: context isolation (D2), the
reveal gate (D1), attitude memory, canon, and conversation history.
**Reconsider if** hosts routinely rebuild the same flag conventions on top
(a sign some progress vocabulary belongs in the layer after all), or if a
standalone-fiction use case returns — that would be a separate front end over
the same two calls, not machinery in the engine.

## D18. `shared_knowledge:` entries — entity-centric shared knowledge, relevance-bounded

**Retrieval portion superseded by D21.** Entity-centric authorship, scoped
entries, condition binding, derived reveal authority, and the separation from
descriptions remain current.
Authored knowledge had two layers — `world.md` (universal) and character
files (individual) — with nothing between. "Anyone in the household knows the
gun cabinet exists" meant either polluting the world bible (narrator included)
or copy-pasting entries across files (they drifted: the brandy-habit entry
existed in two files with different wording). Asked about common knowledge
absent from her file, a character improvised against ground truth she
couldn't see.

*First cut (same day, rejected):* a central `knowledge.yaml` of scope-tagged
pools subscribed via `knowledge_scopes:`. Two flaws killed it within hours. It was
organizationally wrong — a growing junk drawer, when what the world knows
about Lady Ashworth belongs in *her* file like everything else about her.
And it was retrieval-indiscriminate — every subscribed entry entered every
prompt, bloating context and inviting off-topic drift.

*The design:* every entity file (character/item/location) may carry
`shared_knowledge:` — what others know about this entity, by scope (`common` implicit
for everyone; named scopes held via a character's `knowledge_scopes:` list). Entries
have full parity with `knowledge:` entries (`when:` gates,
`reveals`/`why`/`tell`), with `self` bound to the SUBJECT — "about her,
iff she's the culprit" — which deals variant-dependent lore from one shared
block. And retrieval is **bounded by relevance, decided deterministically**:
an entity's about entries are pulled only when it is the addressee, in the
host-declared scene, or mentioned in the message by name/alias. No LLM
judges what a character knows — with one bounded, opt-in exception. Players
The original implementation optionally resolved entity mentions from a public
roster. D21 removed that subject-first mechanism in favor of semantic retrieval
over the already secrecy-filtered knowledge corpus.

The consequential half survives from the first cut: shared entries can carry
`reveals`, which made facts' `revealed_by` field meaningless. **Who can
reveal a fact is derived from the briefing** — own knowledge plus the about
entries actually pulled this turn. This deletes a field, and closes a
coherence gap: a character can only ever reveal what is literally in their
context at that moment, so context and authority cannot desync.

Deliberately NOT auto-derived: entity awareness from `description` fields.
Descriptions are examination-grade and often clue-bearing; what a group
*knows about* a thing is coarser than what examining it shows, and belongs
to the author. Write an about entry.

**Out of scope for now:** second-order knowledge ("the butler knows the
widow knows"). **Reconsider derived-only authority if** an author needs a
character who knows a secret but must NEVER reveal it regardless of gates —
a `never_reveals` marker would be the additive fix.

## D19. Streaming: prose is live, truth is not
In-game, waiting several seconds for a full paragraph kills conversation
flow, so talk and examine both have streaming twins (SSE over HTTP). The
design rule that keeps D1 intact: **only prose streams; truth arrives once,
at the end.** The fenced events block is withheld from the stream by an
incremental fence detector (a held-back tail so a partial fence never
leaks), and `deltas` are emitted only in the final `done` frame,
after the complete reply passes the validation gate — a client that infers
state from streamed words is out of contract. Streaming adds no leak
surface: context isolation happens at assembly, before any token exists,
and validation always ran on the finished reply anyway. Implementation
discipline: each blocking/streaming pair shares its preparation and
application functions, so they cannot drift; `calls.jsonl` still records the
complete exchange. Blocking calls remain the default; streaming changes
transport timing, not the narrative contract.

## D20. One authoritative accessible-item list
DARPS does not model inventory or distinguish possession from proximity. The
host therefore supplies one per-call `world.accessible_items` list, used for
examination authorization, prompt grounding, and shared-knowledge relevance.
Splitting this into carried and nearby lists implied mechanics the engine did
not have and forced every host to translate one accessibility decision into
two fields. An explicit empty list means no pack items are available; omission
keeps the development harness permissive. Unknown world fields fail clearly so
a typo cannot silently widen examination access. Reconsider only if possession
itself gains a distinct narrative rule, in which case add that rule explicitly
rather than splitting accessibility again.

## D21. Scope-first, corpus-wide knowledge retrieval; presence is not memory
Subject-first retrieval failed ordinary questions. If Alice and Halloway share
the `household` scope, Alice should answer "Who makes the cocoa?" from an entry
stored on Halloway even when he is absent and unnamed. Requiring the engine to
identify Halloway before inspecting the entry made that impossible: the topic
that established relevance existed only inside the entry being skipped.

The order is now security first, relevance second. DARPS collects shared
entries across every entity, filters them by the addressed character's scopes
and `when` conditions, and only then retrieves relevant entries from that safe
corpus. Deterministic retrieval includes immediate context, subject names and
aliases, and meaningful content overlap. Optional `knowledge_resolver: true`
adds semantic matches but sees only the safe corpus and returns validated
indexes. Reveal authority remains derived from entries actually selected.

`common` remains implicit for ordinary characters, while
`common_knowledge: false` supports exceptional outsiders or amnesiacs without
removing their named scopes. Descriptions remain excluded: examination-grade
ground truth is not automatically something characters know.

`world.present` is removed. Presence neither grants knowledge nor erases
memory, and DARPS does not implement multi-character dialogue. A future group
conversation feature should introduce explicit participants with defined
speaking semantics rather than overload a world snapshot field.
