# Provider configuration

`config.yaml` has two model slots:

- `model` generates character and narrator prose;
- `classifier_model` performs secret-free screening, mention resolution,
  attitude adjudication, and persona adjudication.

```yaml
provider: openai
model: gpt-4o-mini
classifier_model: gpt-4o-mini
temperature: 0.8
classifier_temperature: 0.0
max_tokens: 700
```

| Provider | Configuration |
|---|---|
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `ollama` | Local server at `localhost:11434` |
| `lmstudio` | Local server at `localhost:1234` |
| `openai_compatible` | `base_url` and `LLM_API_KEY` |
| `litellm` | Optional LiteLLM installation and model strings |

Keep secrets in `.env`, never in a pack. A small local classifier model is
often sufficient, but response quality and strict JSON compliance must be
playtested. Every call is recorded in `logs/calls.jsonl`.

Behavior controls such as tracks, hints, canon, guardrails, history, mention
resolution, and flags files are documented in the
[configuration reference](../reference/configuration.md).
