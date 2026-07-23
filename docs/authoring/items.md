# Items

Items are describable entities, not inventory records. The host tells DARPS
which items are accessible on every call.

```yaml
--8<-- "docs/examples/minimal-pack/items/ledger.yaml"
```

| Field | Purpose |
|---|---|
| `id`, `name` | Stable identity and display name |
| `aliases` | Complete deterministic target-matching vocabulary |
| `description` | Ground truth used when the object is examined |
| `shared_knowledge` | What characters know about the object |
| `examine_reveals` | Facts this item may reveal when examined |
| `hints` | `false` prevents item-targeted hints |

Put every term that should identify the item in `aliases`, including alternate
names, component words, and colloquial references. Location
`search_reveals[].triggers` are different: they gate a particular discovery.

```yaml
examine_reveals:
  - reveals: altered_ledger
    conditions:
      - {flag: workshop_unlocked}
```

DARPS never moves, creates, equips, or persists an item. If a host supplies a
scene with `accessible_items`, only those declared item IDs are eligible
for examination.
