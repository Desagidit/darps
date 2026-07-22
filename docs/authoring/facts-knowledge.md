# Facts and knowledge

```yaml
--8<-- "docs/examples/minimal-pack/facts.yaml"
```

A fact contains:

- a stable `id`;
- prerequisite fact IDs in `requires`;
- optional declarative `conditions`; and
- authoritative player-facing `journal_text`.

Facts do not name their source. Sources live where discovery occurs: character
knowledge, shared knowledge, location search rules, or item examination rules.
This prevents context and reveal authority from drifting apart.

## Shared knowledge

Store shared lore on the entity it describes:

```yaml
shared_knowledge:
  - scope: workshop
    content: Deliveries are recorded in the ledger beside the main bench.
```

An entry reaches a character only when:

1. its scope is `common` (and the character has not opted out) or appears in
   the character's `knowledge_scopes`;
2. its `when` conditions pass; and
3. the safe entry is relevant to the interaction.

DARPS retrieves across all eligible entities, not only people physically in a
scene. Immediate context, subject names/aliases, and meaningful content words
provide deterministic matches. `knowledge_resolver: true` optionally adds
semantic matches from the already secrecy-filtered corpus. See
[Knowledge](../concepts/knowledge.md) for the full model.

## Facts versus canon

Facts are authored, gated, journaled discoveries. Canon records incidental
session truth and has no fact ID or discovery gate. Use facts for gameplay
progress and canon for continuity.
