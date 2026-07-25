# Configuration reference

`config.yaml` is host-owned runtime policy, not pack content.

| Field | Default/example | Meaning |
|---|---|---|
| `provider` | `openai` | Provider adapter or preset |
| `model` | provider-specific | Character/narrator model |
| `classifier_provider` | inherits `provider` | Optional classifier adapter or preset |
| `classifier_model` | provider-specific | Screening and adjudication model |
| `base_url` | provider default | Response-provider endpoint override |
| `classifier_base_url` | classifier provider default | Classifier endpoint override |
| `temperature` | `0.8` | Response-model temperature |
| `classifier_temperature` | `0.0` | Classifier temperature |
| `max_tokens` | `700` | Maximum generated tokens |
| `tracks` | `true` | Enable attitudes; false opens track gates |
| `canon` | `true` | Request, retain, and reuse canon additions |
| `guardrails` | `true` | Screen meta/injection and physics violations |
| `knowledge_resolver` | `false` | Semantic retrieval over the addressee's secrecy-safe shared knowledge |
| `knowledge_cache` | `false` | Optional compiled routing catalogue for common, ungated resolver candidates |
| `knowledge_cache.compression.model` | inherits `model` | One-time semantic catalogue compiler model |
| `knowledge_cache.compression.provider` | inherits `provider` | Provider for the catalogue compiler |
| `knowledge_cache.compression.base_url` | provider default | Optional compiler endpoint override |
| `knowledge_cache.compression.temperature` | `0.2` | Catalogue compiler temperature |
| `knowledge_cache.compression.max_tokens` | `16000` | Maximum compiler output, sized for many routes |
| `examine_resolver` | `false` | Semantic matching over the resolved entity's currently eligible examination trigger groups |
| `strict_items` | `false` | Reject unknown examination targets instead of treating them as parts of the current location |
| `hints.after_turns` | `6` | Relevant fruitless turns before a hint |
| `hints.style` | `subtle` | `subtle`, `pointed`, or `forthcoming` |
| `flags_file` | unset | Host-maintained YAML flags, re-read per call |
| `history_turns` | `12` | Exchanges retained per character |
| `persona_history_turns` | `12` | Inputs retained for persona consistency |

```yaml
provider: ollama
model: llama3.1:8b
classifier_provider: openai
classifier_model: gpt-4o-mini
temperature: 0.8
classifier_temperature: 0.0
max_tokens: 700

tracks: true
canon: false
guardrails: true
knowledge_resolver: false
knowledge_cache: false
examine_resolver: false
strict_items: false
hints: {after_turns: 6, style: subtle}
history_turns: 12
persona_history_turns: 12
```

Omit `classifier_provider` to use `provider` for both model slots. When it is
set, the classifier uses that provider's normal endpoint and credentials;
`base_url` is not inherited across providers. Set `classifier_base_url` only
for a custom classifier endpoint such as an OpenAI-compatible server.

`forthcoming` is the only hint style that changes mechanics: it relaxes
`track_gte` fact gates by one. Entities may opt out of hints with
`hints: false` in their pack file.

`knowledge_cache` matters only with `knowledge_resolver: true`. Set it to
`true` for the default `<pack>/knowledge-cache.yaml`, to a path string, or to
a mapping. Relative paths are resolved from the pack directory:

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

Build the artifact with:

```bash
darps compile-knowledge <pack> --config config.yaml --level 2
```

The compiler uses one model call for levels 1–3. This is an author-time call,
so using a capable model with a large context window does not affect runtime
latency or cost. Level 0 uses full original text and makes no call.

The compiler validates complete ID coverage, uniqueness, non-empty output, and
the per-route word budget before atomically replacing the artifact. If
compilation fails, the previous file is retained. At runtime, a missing, stale,
unreadable, incomplete, or malformed artifact makes DARPS automatically use
the existing full-corpus resolver instead. This changes performance and prompt
size only, never knowledge or reveal authority.
