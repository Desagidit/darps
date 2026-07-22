# Characters

Character files combine identity, performance guidance, private knowledge,
shared reputation, and per-character attitude behavior.

```yaml
--8<-- "docs/examples/minimal-pack/characters/mira.yaml"
```

| Field | Purpose |
|---|---|
| `id` | Stable API and reference identifier |
| `name` | Display name |
| `summary` | Concise role description |
| `aliases` | Names players are likely to use |
| `voice` | Speech rhythm, vocabulary, and mannerisms |
| `background` | Biography that prevents contradictory improvisation |
| `knowledge_scopes` | Named shared-knowledge scopes this character receives |
| `common_knowledge` | `false` opts out of implicit common-scope knowledge |
| `knowledge` | Individual knowledge, optionally gated or revealing facts |
| `shared_knowledge` | What others know about this character |
| `track_settings` | Starting values, speed, and supplemental guidance |
| `track_prose` | Behavioral text selected from current track values |
| `hints` | `false` prevents this character delivering pacing hints |

## Knowledge entries

A plain entry is freely available:

```yaml
- content: The missing clock was booked in on Tuesday.
```

A concealed testimony entry connects knowledge to a fact:

```yaml
- content: The clock arrived after closing.
  reveals: late_delivery
  why: Admitting it would expose an insurance violation.
  tell: She becomes exacting whenever the arrival time is mentioned.
```

`why` and `tell` shape concealment; they do not provide security. Security
comes from context inclusion and engine validation.

## Attitude settings

`start` may be fractional and `speed` must be positive. A model proposes a
coarse shift from -2 to 2; speed scales it before bounds are applied. A speed
of `0.25` therefore makes sustained behavior matter more than one exchange.

Track prose keys are numeric thresholds stored as YAML strings. DARPS selects
the highest threshold not exceeding the current value and supplies only that
prose to the character model.
