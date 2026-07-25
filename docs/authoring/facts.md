# Facts

Sometimes you want to check if a character or description returned by an LLM has revealed something. This cannot be reliably done using traditional game logic but DARPS can analyse responses so your game can react accordingly.
Each pack has its own top-level facts.yaml where facts can be defined.

```yaml
--8<-- "docs/examples/minimal-pack/facts.yaml"
```
A fact contains:

- a stable `id`;
- prerequisite fact IDs in `requires`;
- optional declarative `when` gates; and
- authoritative player-facing `journal_text`.

Facts do not name their source. Sources live where discovery occurs: character knowledge, shared knowledge, location search rules, or item examination rules.
This prevents context and reveal authority from drifting apart.

Let's look at the ledger's yaml file to see where this fact is disclosed.

```yaml
--8<-- "docs/examples/minimal-pack/items/ledger.yaml"
```

# The Journal

The journal is the player-facing result of learned facts. Many games simply won't need or use this but it's provided as a simple way to surface progress in games that are set up to use it.
You can get the current journal [through the API](../api/http-reference.md#post-session).

`GET /journal?session=abc123`

These are UI-friendly views, not independent storage. /journal returns ordered {id, journal_text} objects for learned facts only.

# Facts versus Flags

Facts are DARPS-managed unlocks that usually rely on DARPS analysis of character dialogue or item/location examination.
Flags are game-managed booleans. They are simply a way of the game injecting its state into /talk requests and allowing DARPS to apply conditioning as appropriate.

For example, perhaps writing on a wall is only visible under moonlight. DARPS doesn't know whether it's night time in your game but your game could pass that with a flag.
So you can unlock the fact with a flag like this:

```
id: graffiti-wall
name: the wall
aliases: [wall, bricks]

examine_reveals:
  - reveals: graffiti_message
    when:
      - flag: night
```

Just remember to pass that flag in the API call's world object.

# Facts versus canon

Facts are authored, gated, journaled discoveries. Canon records incidental session truth and has no fact ID or discovery gate. Use facts for gameplay progress and canon for continuity.
