# Pack authoring

A pack is a declarative content bundle. It describes what may be said or
discovered; it does not implement movement, inventory, quests, combat, or
other host-game systems.

```text
pack.yaml          global identity, tracks, persona, hard rails
world.md           setting and voice shared by response contexts
facts.yaml         gated journal truth
vars.yaml          engine-only ground truth
player.yaml        established player role
characters/*.yaml  individual voice, biography, knowledge, attitudes
locations/*.yaml   narration ground truth and search discoveries
items/*.yaml       object ground truth and examination discoveries
prompts/*.txt      optional advanced prompt overrides
```

## Authoring loop

```bash
python -m darps new packs/my-game
python -m darps validate packs/my-game
python -m darps play packs/my-game
```

Edit YAML, validate, and then playtest. When play behaves strangely, inspect
`logs/calls.jsonl` before changing content: it records the exact scoped prompt,
response, call tag, and latency.

## Facts are the spine

Every learnable truth must be declared once in `facts.yaml` and have a source:

- a character `knowledge` entry;
- a relevant entity's `shared_knowledge` entry;
- a location `search_reveals` rule; or
- an item `examine_reveals` rule.

The source and fact gates must both pass. Generated prose alone never teaches
the player a fact.
