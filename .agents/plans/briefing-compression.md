# Briefing compression plan

## Goal

Optionally reduce large character prompts without weakening context isolation,
fact authority, or authored behavioral constraints.

This is a future feature, not current behavior.

## Proposed host configuration

```yaml
briefing_summary:
  level: 0          # 0 off; 1 light; 2 moderate; 3 aggressive
  after_chars: 16000
```

`level: 0` makes no summary call. Levels 1–3 select progressively smaller
targets, but compression runs only after the compressible source exceeds
`after_chars`.

## Safety boundary

The summarizer may see only context already permitted in the addressed
character's briefing. It must never receive gated-out knowledge, `vars.yaml`,
other characters' private knowledge, or undiscovered facts.

These blocks remain verbatim at every level:

- system/roleplaying rules and the events contract;
- current player input and tone;
- current attitude prose;
- exact established canon;
- exact learned journal entries;
- world/accessibility grounding;
- every reveal-bearing entry, including fact ID, `why`, and `tell`.

Initially compress only:

- biography/background;
- non-revealing private knowledge;
- non-revealing retrieved shared knowledge;
- older conversation history;
- repeated descriptive context.

Reveal authority continues to be calculated from the original gated entries,
never from a generated summary.

## Level semantics

- **1 — light:** compact older conversation history and obvious repetition.
- **2 — moderate:** additionally compact biography and ordinary lore.
- **3 — aggressive:** use a smaller target for every compressible section,
  while preserving all authoritative blocks above.

The levels should map to documented character/token budgets rather than vague
prompt adjectives.

## Implementation outline

1. Instrument call logs with prompt character counts and section sizes.
2. Refactor character prompt assembly into named authoritative and
   compressible sections.
3. Add a default `briefing_summary.txt` prompt returning a structured summary.
4. Validate the summary shape and fail open to the original verbatim context
   on malformed output or provider failure, subject to the normal provider
   error policy.
5. Add exact-source-hash caching described in
   `briefing-summary-cache.md`.
6. Preserve prompt overrides and pack hot reload by including prompt/content
   fingerprints in cache keys.

## Tests

- Level 0 makes no additional call and produces the existing prompt.
- Below-threshold content makes no summary call.
- Gated-out secrets never enter the summary prompt.
- Reveal-bearing entries remain verbatim and reveal authority is unchanged.
- Invalid summary output falls back safely.
- Levels produce monotonically smaller configured targets.
- Pack edits invalidate summaries.

## Open decisions

- Whether to use `classifier_model` by default or add a dedicated summary
  model override.
- Whether provider failure should fall back verbatim or fail the turn.
- Exact character budgets for levels 1–3 after real prompt measurements.
