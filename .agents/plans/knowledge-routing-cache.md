# Compiled common-knowledge routing catalogue

## Status

Implemented.

## Purpose

Reduce the token size of the optional semantic knowledge-resolver call in
large packs without changing character briefings or reveal authority.

## Author workflow

```bash
darps compile-knowledge <pack> --level 2
```

The default output is `<pack>/knowledge-cache.yaml`. It is inspectable and
suitable for committing with the pack. Levels 1–3 use one author-time semantic
compression call; level 0 copies full text without a call.

## Runtime configuration

```yaml
knowledge_resolver: true
knowledge_cache:
  enabled: true
  path: knowledge-cache.yaml
  compression:
    provider: openai
    model: large-context-model
    temperature: 0.2
    max_tokens: 16000
```

`knowledge_cache` may alternatively be a pack-relative/absolute path or an
`{enabled, path}` mapping.

The compiler receives the config through
`darps compile-knowledge <pack> --config config.yaml`. The compression model is
independent of the runtime response and classifier models.

## Safety contract

- Compile only `scope: common` entries with no non-empty `when`.
- Store routing labels and source fingerprints, not authoritative replacement
  knowledge.
- Require exactly one semantic route per stable input ID and enforce the
  level's word budget.
- Replace an existing artifact atomically only after complete validation.
- Filter the live corpus by scope and gates before retrieval as before.
- Translate selected catalogue routes back to exact live YAML entries.
- Derive reveal authority only from those restored exact entries.
- Fall back wholesale to full resolver content on every artifact problem.
- Keep deterministic retrieval, named scopes, and conditional entries live.

## Deferred extensions

- Author-approved world-lore summaries. `world.md` mixes lore and hard rules,
  so automatic compression is not yet safe.
- Flag-variant catalogues. Conditional entries remain live to avoid invalid
  cache-key and combinatorial-variant complexity.
