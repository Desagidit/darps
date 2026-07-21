# Configuration reference

`config.yaml` is host-owned runtime policy, not pack content.

| Field | Default/example | Meaning |
|---|---|---|
| `provider` | `openai` | Provider adapter or preset |
| `model` | provider-specific | Character/narrator model |
| `classifier_model` | provider-specific | Screening and adjudication model |
| `base_url` | provider default | Endpoint override |
| `temperature` | `0.8` | Response-model temperature |
| `classifier_temperature` | `0.0` | Classifier temperature |
| `max_tokens` | `700` | Maximum generated tokens |
| `tracks` | `true` | Enable attitudes; false opens track gates |
| `canon` | `true` | Request, retain, and reuse canon additions |
| `guardrails` | `true` | Screen meta/injection and physics violations |
| `mention_resolver` | `false` | Classifier fallback for loose entity mentions |
| `hints.after_turns` | `6` | Relevant fruitless turns before a hint |
| `hints.style` | `subtle` | `subtle`, `pointed`, or `forthcoming` |
| `flags_file` | unset | Host-maintained YAML flags, re-read per call |
| `history_turns` | `12` | Exchanges retained per character |
| `persona_history_turns` | `12` | Inputs retained for persona consistency |

```yaml
provider: ollama
model: llama3.1:8b
classifier_model: llama3.1:8b
temperature: 0.8
classifier_temperature: 0.0
max_tokens: 700

tracks: true
canon: false
guardrails: true
mention_resolver: false
hints: {after_turns: 6, style: subtle}
history_turns: 12
persona_history_turns: 12
```

`forthcoming` is the only hint style that changes mechanics: it relaxes
`track_gte` fact gates by one. Entities may opt out of hints with
`hints: false` in their pack file.
