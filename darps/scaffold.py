"""darps new <dir> — scaffold a minimal, valid pack with two characters, three
facts, and comments explaining every field. The on-ramp for a stranger:
install, scaffold, edit YAML, validate, serve (or `darps play` to drive it by
hand).

DARPS is a conversation layer: the host game says WHO is being addressed and
WHERE, and injects progress FLAGS; the pack declares what characters know,
what they hide, and what gates each disclosure."""
from pathlib import Path

FILES = {
"pack.yaml": '''# DARPS pack manifest. Run `darps validate .` after every edit.
name: My First Pack
author: you
player_label: "the visitor"          # how prompts refer to the player character
start_location: parlor               # fallback when a call omits world.location

impossible: "leaving the house, violence beyond a shove, anything supernatural"
meta_response: "The house creaks. Whatever you were reaching for, it isn't here."

# Sentiment: numeric relationship tracks, engine-held; characters perform
# author-written prose per threshold, never numbers. The host's config.yaml
# can disable the whole mechanic with `tracks: false`.
tracks:
  disposition:
    min: -3
    max: 3
    default: 0
    guidance: >
      Kindness and respect increase it; hostility and contempt decrease it.
      Routine questions and repeated pleasantries do not change it.
  fear:
    min: 0
    max: 3
    default: 0
    guidance: >
      Credible threats increase it; bluster does not; reassurance reduces it.
default_track: disposition

# Session-wide player judgments: separate from per-character attitude tracks,
# updated from both talk and examine inputs, and never shown to response models.
persona:
  role_consistency:
    min: -3
    max: 3
    default: 0
    speed: 0.25
    guidance: >
      Reward choices and speech consistent with the established inheritor.
      Neutral actions score zero. Penalize knowingly contradicting the player
      biography or acting on information not yet discovered.
''',
"vars.yaml": '''# Ground truth. Engine-only — reaches an LLM context ONLY via
# `when`-gated knowledge entries. Keep this file out of screenshots.
keeper: mara
''',
"world.md": '''# World Bible — always in context

An old house at the end of a lane; the player is a visitor who has inherited
it, sight unseen. Tone: quiet, uncanny, warm underneath. Second person present
tense for narration. Keep responses under 120 words. Never mention game
mechanics. Never invent significant facts beyond what instructions authorize.
''',
"facts.yaml": '''# The fact web. `requires` gates on other facts; `conditions`
# uses the DARPS condition vocabulary (see SPEC.md §6).
- id: hidden_door
  requires: []
  journal_text: >-
    Behind the bookcase, a narrow door — painted over, but its hinges are new.

- id: old_photo
  requires: [hidden_door]
  journal_text: >-
    Inside the doorway, a photograph: the housekeeper Mara, unmistakably her,
    standing before this house. The print is dated sixty years ago.

# Testimony: WHO can reveal this is derived from knowledge entries that
# `reveals:` it (Mara's file does). No revealed_by field.
- id: keepers_admission
  requires: [old_photo]
  conditions:
    - {track_gte: {track: disposition, value: 1}}
  journal_text: >-
    Mara admits she has kept this house — and its door — far longer than any
    housekeeper could.
''',
"player.yaml": '''# The protagonist (optional file). `description` is injected into every
# LLM context. What the player carries is the HOST's business, declared per
# call via world.accessible_items — not pack content.
name: The Inheritor
description: >
  You inherited this house from a relative you never met. You are curious,
  a little out of your depth, and carrying nothing but the solicitor's key.
''',
"items/house_key.yaml": '''# An item is a DESCRIBABLE ENTITY: ground truth for narration when the
# host says it is available (world.accessible_items). DARPS never
# moves or tracks items — the host owns the world.
id: house_key
name: the solicitor's key
aliases: [key, iron key, solicitor, house key, the key] # matching vocabulary
description: >
  Old iron, older wards. The tag reads only the house's name.
# examine_reveals: [{reveals: some_fact}] # examining it may surface facts,
#                                        # through the normal fact gates
''',
"characters/mara.yaml": '''id: mara
name: Mara
summary: the housekeeper who came with the house
aliases: [the housekeeper, Mrs. Mara]   # names the player might use for her;
                                        # also drive shared-knowledge relevance

# What others know ABOUT Mara, by scope (her own knowledge goes under
# `knowledge:` below — different axis).
shared_knowledge:
  - content: "Mara came with the house; the solicitor's letter never mentioned her."
  - scope: village
    content: "Mara was already old when today's grandparents were young — so they say."

voice: >
  Unhurried, courteous, faintly amused. Answers exactly what is asked.

background: >
  She was here when you arrived. The solicitor's letter did not mention her.

# Unified knowledge model: plain entries are freely shareable; `reveals`
# entries carry a disclosure policy; `when` entries only enter context if
# the conditions hold (this is the context-isolation secrecy mechanism).
# HOST FLAGS are the progress signal: the game injects them per call (or
# keeps a flags file up to date), and knowledge gates on them — including
# negations, for lies that expire.
knowledge:
  - content: "The house has been in the family a long time. Longer than most think."
  - content: "She dusts the bookcase every day, and never moves it."
    reveals: keepers_admission
    why: "Sixty years of quiet is a habit not easily broken."
    tell: "Her dusting slows when the bookcase is mentioned."
  # A LIE with an expiry: only in context until the host sets door_opened.
  - content: >
      If asked about the bookcase wall, you say there is nothing behind it —
      just damp and bad plaster. You say this pleasantly and change the subject.
    when:
      - {not: {flag: door_opened}}
  # Truth that ACTIVATES when the host signals progress.
  - content: >
      The door stands open now; there is no point pretending. You may speak of
      the passage plainly, though not yet of what you are.
    when:
      - {flag: door_opened}
  - content: >
      YOU are the keeper. You have tended this house for sixty years without
      aging a day, and the door behind the bookcase is the reason. If the
      visitor earns your trust and holds the photograph, you may finally say so.
    when:
      - {var: keeper, is: self}

track_settings:
  disposition:
    start: -0.5
    speed: 0.5
    guidance: >
      Warmth opens her; rudeness meets a closed, polite surface. She cannot be
      intimidated — only trusted.
  fear:
    start: 0
    speed: 0.5
    guidance: "Threats to the house affect her more than threats against herself."

track_prose:
  disposition:
    "-2": "Mara is a sealed room. Single sentences, perfect courtesy, nothing given."
    "0": "Mara is pleasant and unforthcoming, a housekeeper and nothing more."
    "1": "Mara lingers in doorways now, as if deciding something about you."
  fear:
    "0": "Mara is entirely at ease in her own house."
    "1": "Mara watches the visitor with new caution."
''',
"characters/tom.yaml": '''id: tom
name: Tom Brandt
summary: the neighbour who keeps dropping by
aliases: [the neighbour, Mr. Brandt]
hints: false          # this character never delivers pacing hints
knowledge_scopes: [village] # receives village-scoped shared knowledge
                      # (`common` is implicit for everyone)
# common_knowledge: false   # rare opt-out for an outsider/amnesiac/etc.;
#                           # defaults to true

voice: >
  Chatty, kind, a little lonely. Talks with his hands.

background: >
  Retired postman. Has lived on the lane forty years and noticed things.

# Note: what Tom knows ABOUT Mara and the parlor comes from their shared knowledge
# sections (he holds the `village` scope) — no duplication here.
knowledge:
  - content: "His mother swore the lane was different before Mara's time. She never said how."

track_settings:
  disposition:
    start: 0.5
    speed: 0.75
    guidance: "Friendly treatment raises it; bullying makes him clam up from hurt."
  fear:
    start: 0
    speed: 0.75

track_prose:
  disposition:
    "0": "Tom is friendly and glad of the company."
  fear:
    "0": "Tom is relaxed."
    "1": "Tom grows nervous and glances toward the lane."
''',
"locations/parlor.yaml": '''id: parlor
name: The Parlor
aliases: [the sitting room, the front room]

# `shared_knowledge:` = what OTHERS know about this entity, by scope.
# character's briefing only when this entity is RELEVANT to the turn (it's
# the scene, or the player's message mentions it by name/alias) AND the
# character holds the entry's scope (`common` is the default — everyone).
shared_knowledge:
  - content: >
      The parlor bookcase is famously never moved, not even for cleaning —
      it has stood against that wall for as long as anyone remembers.
  - scope: village              # characters declaring this knowledge scope
    content: >
      Children dare each other to touch the parlor window at dusk. Nobody
      remembers who started it.
    when:
      - {not: {flag: door_opened}}       # gates work here too; `self` binds to
                                         # the SUBJECT (this location)

description: >
  Dust sheets pulled from good furniture, a cold hearth, and a bookcase far
  too heavy for its wall. Mara stands ready with tea; Tom has let himself in.

search_reveals:
  - reveals: hidden_door
    where: the bookcase and the wall behind it
    triggers: [bookcase, books, shelf, wall, behind]
  - reveals: old_photo
    where: through the painted-over door
    triggers: [door, doorway, inside, through, photo]

scenery: >
  Water-stained ceiling roses; a stopped clock; a rug worn in a path that
  leads to the bookcase and nowhere else.
''',
}


def scaffold(dest: str | Path) -> Path:
    root = Path(dest)
    if (root / "pack.yaml").exists():
        raise FileExistsError(f"{root}/pack.yaml already exists")
    for rel, body in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root
