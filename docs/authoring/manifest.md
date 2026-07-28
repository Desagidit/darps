# Pack manifest

`pack.yaml` defines global pack identity, hard rails, attitude tracks, and
optional player-persona dimensions.

```yaml
--8<-- "docs/examples/minimal-pack/pack.yaml"
```

| Field | Required | Purpose |
|---|---:|---|
| `name` | Yes | Display name and basis of the state `pack_id` |
| `start_location` | Yes | Fallback location when the host omits one |
| `author` | No | Attribution |
| `player_label` | No | How prompts refer to the player |
| `impossible` | No | Prose describing actions that violate the fiction |
| `meta_response` | No | In-fiction response to out-of-fiction/injection input |
| `tracks` | No | Shared bounds, starts, speeds, and guidance for attitudes |
| `default_track` | No | Track changed when `adjust_track` omits a track |
| `persona` | No | Session-wide player judgements |

Each track may define a positive `speed`, which defaults to `1.0`. That speed
scales every adjudicated change unless a character supplies an override in
`track_settings`. Pack tracks and character settings use the same field names:
`min`, `max`, `start`, `speed`, and `guidance`. Character fields override pack
fields individually. Track guidance must explain positive, negative, and
neutral input. Persona guidance should judge the player role rather than an
NPC's feelings.

!!! warning
    Never place hidden plot truth in track or persona guidance. Classifier
    prompts are intentionally secret-free.
