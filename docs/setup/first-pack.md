# Create your first pack

Scaffold a complete, commented pack:

```bash
python -m darps new packs/my-game
python -m darps validate packs/my-game
```

A pack contains authored content, not executable logic:

```text
my-game/
├── pack.yaml
├── world.md
├── facts.yaml
├── player.yaml
├── vars.yaml
├── characters/
├── locations/
└── items/
```

The documentation includes a small working pack at
`docs/examples/minimal-pack`. Run it directly:

```bash
python -m darps validate docs/examples/minimal-pack
python -m darps play docs/examples/minimal-pack
```

Use it to learn the core chain:

1. `facts.yaml` declares what the player can learn.
2. A character knowledge entry, location search rule, or item examination rule
   provides a source for each fact.
3. Conditions decide whether the source is currently permitted.
4. The model may propose a reveal; the engine verifies it.
5. Approved facts enter the journal using their exact `journal_text`.

!!! tip
    Run `darps validate` after every editing round. It detects missing
    references, impossible gates, unreachable facts, invalid track prose, and
    other authoring mistakes before an LLM call costs time or money.
