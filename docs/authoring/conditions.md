# Conditions

DARPS uses a closed condition vocabulary. Lists are logical AND; there is no
arbitrary expression language.

| Form | True when |
|---|---|
| `{var: name, is: value}` | Engine-only `vars.yaml` value matches |
| `{fact_learned: fact_id}` | Player already holds the fact |
| `{flag: name}` | Host flag is truthy |
| `{track_gte: {track: t, value: n, of: character?}}` | Track meets threshold |
| `{not: condition}` | One valid wrapped condition is false |

Examples:

```yaml
when:
  - {var: keeper, is: self}
  - {not: {flag: confession_complete}}
```

```yaml
conditions:
  - {fact_learned: altered_ledger}
  - {track_gte: {track: disposition, value: 1}}
```

`self` means the character in individual knowledge and the subject entity in
shared knowledge. Unknown or malformed conditions fail closed and are pack
validation errors. Negation cannot wrap another `not` directly.

Flags belong to the host, so their names cannot be statically verified. Keep a
commented list of the host/pack flag contract near the relevant content.
