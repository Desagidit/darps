# Glossary

**Alias**
: A player-facing alternate name for a character, location, or item. Aliases
  support deterministic matching and shared-knowledge relevance.

**Attitude adjudication**
: A secret-free classifier pass that judges how the current player message
  changes each declared character track.

**Canon**
: Session truth created through accepted model improvisation or `add_canon`.
  Canon is not a gated journal fact.

**Character**
: An addressable conversational entity. A character defines identity, voice,
  private knowledge, reveal permissions, and per-character attitude tracks.

**Classifier**
: The cheaper model slot used for input screening, mention resolution,
  attitudes, and persona. Classifier contexts contain no hidden story truth.

**Condition**
: A declarative gate from DARPS's closed vocabulary, such as `flag`,
  `fact_learned`, or `track_gte`.

**Delta**
: A validated state change returned to the host, including changed tracks,
  persona values, facts learned, and canon added.

**Entity**
: A character, location, or item with an ID, display name, aliases, and
  optional shared knowledge.

**Events block**
: Structured JSON proposed by a response model alongside prose. DARPS removes
  it from display text and validates every field.

**Fact**
: A gated, authored piece of truth the player may learn and record in the
  journal.

**Flag**
: Host-owned progress state injected through the world snapshot or flags file.

**Fruitless turn**
: A story-relevant interaction that learned no fact. Consecutive fruitless
  turns drive optional hints.

**Guidance**
: Secret-free adjudication criteria describing what raises, lowers, or leaves
  a track or persona dimension unchanged.

**Host**
: The game integrating DARPS and owning world simulation and persistence.

**Item**
: A host-owned world object whose pack entry supplies descriptive context,
  aliases, examination behavior, reveals, and shared knowledge.

**Journal**
: The player-facing collection of learned facts. Its entries are the
  `journal_text` values of those facts, in discovery order.

**Journal text**
: The exact authored player-facing description stored when a fact is learned.

**Knowledge**
: Information placed in one character's briefing when its conditions pass.

**Knowledge scope**
: A subscription controlling which scoped shared-knowledge entries a character
  receives. `common` is implicit for everyone.

**Location**
: A host-owned place whose pack entry supplies conversational atmosphere,
  aliases, examination behavior, reveals, and shared knowledge.

**Pack**
: A directory of declarative game content consumed by DARPS.

**Pack ID**
: The stable identifier in `pack.yaml` used to select a pack when creating an
  API session.

**Persona**
: Session-wide, player-centric judgements that never shape response prompts.

**Prompt override**
: A pack-local template in `prompts/` that replaces an engine default. Use one
  only when the pack needs a genuinely different response contract.

**Reveal authority**
: Permission for the current character or examination to reveal a particular
  fact this turn, derived from its actual scoped context and gates.

**Shared knowledge**
: Lore stored on the entity it describes and retrieved only when that entity
  is relevant and the receiving character holds its scope.

**State**
: DARPS-owned narrative memory: learned facts, tracks, persona, canon,
  conversations, and fruitless-turn counters. Host-owned world state is not
  part of it.

**Story relevance**
: A clamped response event indicating how strongly an exchange engaged the
  central matter; used only for pacing.

**Track**
: A bounded per-character attitude such as disposition, fear, or suspicion.

**Track prose**
: Authored behavioral bands selected from numeric track values. Models see the
  prose, never the numbers.

**World snapshot**
: Ephemeral host state supplied for one call: location, presence, accessible
  items, and flags. It is never persisted by DARPS.
