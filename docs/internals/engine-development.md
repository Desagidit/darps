# Modifying the engine

Read [design decisions](../DECISIONS.md) before redesigning behavior. Many
apparently local changes cross the pack contract, static validator, runtime
gate, prompts, state, and clients.

## Change obligations

| Change | Required companion work |
|---|---|
| Condition vocabulary | `conditions.py`, lint semantics, pack spec, tests |
| Model event field | Prompt schema, `validate.py`, spec, tests |
| Pack schema | Spec, lint, scaffold, reference pack, tests |
| State shape | Initial state, normalization, API docs, save tests |
| Result shape | Spec, CLI, HTTP, C# client, tests |
| General behavior prose | Default prompt plus assembled-prompt test |

## Development workflow

```bash
python tests/smoke.py
python -m darps validate packs/ashworth-manor
python -m darps new /tmp/darps-check
python -m darps validate /tmp/darps-check
```

Tests stub `darps.llm.call`; they must never require a key or network. Add a
numbered smoke group for every behavior change and test both allowed and
blocked paths.

## Debug before changing

Start with `logs/calls.jsonl` and classify the failure:

1. **Pack data:** the context lacks authored information or guidance.
2. **Prompt contract:** the prompt requests behavior without supplying the
   information needed to perform it.
3. **Engine behavior:** deterministic authorization, validation, state, or
   transport is wrong.

Fix in that order: pack data, general prompt, deterministic engine layer.
Critical truth and secrecy behavior always receives an engine guarantee.

## Invariants

- The host owns the world; DARPS owns narrative memory.
- Models propose; the validator disposes.
- False knowledge gates mean the text is absent.
- Numbers remain in the engine; prompts receive behavioral prose.
- Unknown or malformed conditions fail closed.
- Pack functionality stays declarative whenever possible.
