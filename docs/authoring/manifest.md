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
| `tracks` | No | Shared bounds, defaults, and guidance for attitudes |
| `default_track` | No | Track changed when `adjust_track` omits a track |
| `persona` | No | Session-wide player judgements |

Track guidance must explain positive, negative, and neutral input. Persona
guidance should judge the player role rather than an NPC's feelings.

!!! warning
    Never place hidden plot truth in track or persona guidance. Classifier
    prompts are intentionally secret-free.
