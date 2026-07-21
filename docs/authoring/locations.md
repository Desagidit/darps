# Locations

Locations ground narration and authorize discoveries from free-text searches.

```yaml
--8<-- "docs/examples/minimal-pack/locations/workshop.yaml"
```

| Field | Purpose |
|---|---|
| `id`, `name`, `aliases` | Identity and matching |
| `description` | Examination-grade ground truth |
| `scenery` | Safe atmospheric details the narrator may use |
| `shared_knowledge` | What relevant characters know about the place |
| `search_reveals` | Triggered fact sources for searching this location |
| `hints` | `false` disables narrator pacing hints here |

Each search rule identifies a fact, player vocabulary, and a useful hint
target:

```yaml
search_reveals:
  - reveals: altered_ledger
    where: the delivery ledger beside the main bench
    triggers: [ledger, book, deliveries, ink, entry]
```

Triggers should contain nouns and verbs players will actually type. The model
does not decide whether the fact is discoverable: DARPS matches the trigger
and evaluates the fact gates before constructing the narrator prompt.
