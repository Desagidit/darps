# Common recipes

## Start a character guarded

```yaml
track_settings:
  disposition:
    start: -1
    speed: 0.25
```

Write track prose at and below `-1`, then explain in guidance what earns trust.

## Add testimony

1. Declare the fact and journal text.
2. Add `reveals: fact_id` to the speaker's knowledge.
3. Add `why` and `tell`.
4. Add fact prerequisites or conditions.
5. Validate and test below/above every threshold.

## Expire a lie with a flag

```yaml
- content: Mira insists the delivery arrived before closing.
  when:
    - {not: {flag: ledger_confronted}}

- content: Mira acknowledges the altered time and explains why she changed it.
  when:
    - {flag: ledger_confronted}
```

The host starts sending `ledger_confronted: true` after its own confrontation
logic succeeds.

## Add a custom track

Declare shared bounds and guidance in `pack.yaml`, then add character-specific
starts, speed, supplemental guidance, and prose bands:

```yaml
tracks:
  suspicion:
    min: 0
    max: 4
    default: 0
    guidance: Evidence of deception raises suspicion; transparent explanations lower it.
```

## Support multiple save slots

For each slot, store both host state and the complete DARPS `state` object.
Loading a slot may create a fresh live session:

```text
slot A state -> POST /session -> session A
slot B state -> POST /session -> session B
```

Sessions are independent and may coexist. Close abandoned sessions after a
load transition.

## Advance narrative state from a cutscene

```http
POST /grant_fact   {"session":"...","fact":"altered_ledger"}
POST /add_canon    {"session":"...","text":"The alarm failed at 9:30 pm."}
POST /adjust_track {"session":"...","character":"mira","change":1}
```

These calls make no model request.

## Debug unexpected dialogue

1. Open the latest matching entry in `logs/calls.jsonl`.
2. Identify its tag: `classifier`, `attitudes:<id>`, `persona`,
   `character:<id>`, or `narrator`.
3. Check whether the prompt contained the required data and excluded secrets.
4. Classify the failure as content, prompt contract, or deterministic engine
   behavior.
5. Add a stubbed regression test before changing general engine behavior.
