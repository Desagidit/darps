# Provider configuration

`config.yaml` has two runtime model slots:

- `model` generates character and narrator prose;
- `classifier_model` performs secret-free screening, mention resolution,
  attitude adjudication, and persona adjudication.

An optional third model is used only by the author tool:

- `knowledge_cache.compression.model` creates semantic routing labels when
  running `darps compile-knowledge`.

```yaml
provider: openai
model: gpt-4o-mini
classifier_provider: openai
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

## Separate response and classifier providers

`classifier_provider` is optional and inherits `provider`. Set it when a
different service is cheaper, faster, or better suited to structured
classification:

```yaml
provider: anthropic
model: claude-sonnet-4-5-20250929

classifier_provider: openai
classifier_model: gpt-4o-mini
```

Each native provider reads its usual environment variable, so this example
uses `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`. `base_url` applies to the
response provider. An explicitly separate classifier uses its provider preset
unless `classifier_base_url` is also set.

Keep secrets in `.env`, never in a pack. A small local classifier model is
often sufficient, but response quality and strict JSON compliance must be
playtested. Every call is recorded in `logs/calls.jsonl`.

The knowledge compiler can use a different, larger-context provider without
affecting shipped runtime cost:

```yaml
knowledge_cache:
  enabled: true
  compression:
    provider: openai
    model: large-context-model
    temperature: 0.2
    max_tokens: 16000
```

Omitted compression fields inherit the response provider and model. The
compiler makes one call for levels 1–3 and logs it as `knowledge-compile`.

Behavior controls such as tracks, hints, canon, guardrails, history, mention
resolution, and flags files are documented in the
[configuration reference](../setup/configuration.md).
