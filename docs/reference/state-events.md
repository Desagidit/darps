# State and events reference

## State

```json
{
  "state_version": 1,
  "pack_id": "workshop-ledger",
  "turn": 4,
  "facts_learned": ["altered_ledger"],
  "tracks": {"disposition": {"mira": 0.5}},
  "canon": ["The alarm was disabled at 9:30 pm."],
  "conversations": {
    "mira": [{"player":"When did it arrive?","reply":"Before closing."}]
  },
  "fruitless_turns": 1,
  "persona": {"careful_investigator": 0.25},
  "persona_history": [{"kind":"talk","input":"When did it arrive?"}]
}
```

The blob is opaque host persistence data. Store it whole rather than
constructing fields manually.

## Character events

When canon is enabled, the model contract is:

```json
{
  "reveals": ["fact_id"],
  "canon_additions": ["short concrete statement"],
  "story_relevance": 0
}
```

`story_relevance` clamps from 0 to 2 and defaults to 1. Canon additions are
limited and discarded entirely when canon is disabled.

## Narrator events

```json
{
  "reveals": ["fact_id"],
  "story_relevance": 2
}
```

The narrator can reveal only facts pre-authorized from the current location or
reachable item. Invented IDs and unauthorized discoveries are stripped.

## Classifier proposals

Attitudes and persona use:

```json
{"shifts":{"dimension_or_track_id":-1}}
```

Unknown IDs disappear; shifts clamp to -2 through 2 before speed and bounds
are applied.
