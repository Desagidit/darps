# Locations

Locations ground narration and authorize discoveries when the player examines
the place or one of its named areas.

```yaml
--8<-- "docs/examples/minimal-pack/locations/workshop.yaml"
```

| Field | Purpose |
|---|---|
| `id`, `name`, `aliases` | Identity and matching |
| `description` | Examination-grade ground truth |
| `scenery` | Safe atmospheric details the narrator may use |
| `shared_knowledge` | What relevant characters know about the place |
| `examine_reveals` | Fact sources for examining this location |
| `hints` | `false` disables narrator pacing hints here |

Each rule identifies a fact, optional matching vocabulary, and a useful hint
target:

```yaml
examine_reveals:
  - reveals: altered_ledger
    where: the delivery ledger beside the main bench
    triggers: [ledger, book, deliveries, ink, entry]
    when:
      - flag: workshop_unlocked
```

Omit `triggers` when a general look around should be sufficient. Otherwise,
use nouns and verbs players will actually type. The model does not decide
whether the fact is discoverable: DARPS matches any required trigger and
evaluates the source's `when` gates followed by the linked fact's gates before
constructing the narrator prompt. Host config `examine_resolver: true` may add
semantic trigger matches from this entity's eligible rules; all gates remain
engine-enforced.
