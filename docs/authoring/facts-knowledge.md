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

1. its subject is relevant to this interaction;
2. its scope is `common` or appears in the character's `knowledge_scopes`;
3. its `when` conditions pass.

Relevant subjects are the addressee, host-declared scene entities, and entities
mentioned by ID, name, or alias. `mention_resolver: true` adds a classifier
fallback for misspellings and loose descriptions.

## Facts versus canon

Facts are authored, gated, journaled discoveries. Canon records incidental
session truth and has no fact ID or discovery gate. Use facts for gameplay
progress and canon for continuity.
