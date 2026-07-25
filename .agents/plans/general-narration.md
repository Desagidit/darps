# General narration plan

## Goal

Add display-only host narration for scene introductions, transitions,
atmosphere, weather, and host-controlled events without pretending the player
examined something.

## Public API

Library:

```python
Game.narrate(instruction="", *, world=None, tone=None) -> result
Game.narrate_stream(instruction="", *, world=None, tone=None) -> events
```

HTTP:

```http
POST /narrate
POST /narrate/stream
```

Body:

```json
{
  "session": "SESSION_ID",
  "instruction": "Describe the storm worsening as the lights fail.",
  "world": {
    "location": "study",
    "accessible_items": ["brandy_glass"],
    "flags": {"power_failed": true}
  },
  "tone": "ominous"
}
```

`instruction` is optional and defaults to “Describe the current scene
briefly.” It is called an instruction rather than a prompt because hosts do
not replace DARPS's underlying safety/context template.

## Truth and state contract

General narration is display-only:

- no fact reveals;
- no track or persona adjudication;
- no canon additions;
- no conversation or persona history;
- no fruitless-turn or hint-pacing changes;
- no turn increment;
- no autosave;
- no input-classifier call.

The host remains authoritative over progression. A cutscene that teaches a
fact should call `/grant_fact`, then `/narrate` to portray it.

The result retains the common response shape with `speaker: null` and empty
deltas. Streaming emits prose chunks followed by the same final result.

## Context boundary

The narration model may receive:

- `world.md` and player identity;
- current location description/scenery;
- host-declared accessible item names, IDs, and descriptions;
- exact learned journal entries;
- enabled canon;
- host instruction and tone;
- public physics rules from the manifest.

It must not receive:

- `vars.yaml`;
- undiscovered fact definitions;
- private or shared character knowledge;
- examination reveal rules or trigger groups;
- track/persona values or criteria.

The prompt permits only inconsequential sensory improvisation and forbids
inventing significant objects, discoveries, actions, or state changes.

## Implementation checklist

- [x] Add `narrate.txt` default prompt and pack override contract.
- [x] Add blocking and streaming `Game` methods sharing prompt preparation.
- [x] Add HTTP routes and safe `/pack` capabilities.
- [x] Add C# client methods.
- [x] Document library/API contracts and update architecture diagrams.
- [x] Record the accepted design in `DECISIONS.md`.
- [x] Add stubbed tests for context isolation, zero mutation, default
      instruction, world grounding, blocking output, and streaming truth.
- [x] Validate Ashworth, a fresh scaffold, Python compilation, and MkDocs.
