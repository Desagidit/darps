# `when` gates

DARPS uses a closed gate vocabulary under the `when` field. Lists are logical
AND; use `any` for explicit alternatives. There is no arbitrary expression
language.

| Form | True when |
|---|---|
| `{var: name, is: value}` | Engine-only `vars.yaml` value matches |
| `{fact_learned: fact_id}` | Player already holds the fact |
| `{flag: name}` | Host flag is truthy |
| `{track_gte: {track: t, value: n, of: character?}}` | Track meets threshold |
| `{any: [condition, ...]}` | At least one condition in the non-empty list is true |
| `{not: condition}` | One valid wrapped condition is false |

Examples:

```yaml
when:
  - {var: keeper, is: self}
  - {not: {flag: confession_complete}}
```

```yaml
when:
  - fact_learned: altered_ledger
  - track_gte:
      track: disposition
      value: 1
```

Alternative routes are grouped under `any` while the surrounding `when`
conditions still all apply:

```yaml
when:
  - fact_learned: cellar_map
  - any:
      - flag: cellar_open
      - flag: steward_has_key
      - fact_learned: cellar_key
```

`self` means the character in individual knowledge and the subject entity in
shared knowledge. Unknown or malformed gates fail closed and are pack
validation errors. `any` must contain at least one condition. Negation cannot
wrap another `not` directly.

Flags belong to the host, so their names cannot be statically verified. Keep a
commented list of the host/pack flag contract near the relevant content.
