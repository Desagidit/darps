# Mental model

DARPS divides responsibility deliberately:

| Owner | Responsible for |
|---|---|
| Host game | All game logic as usual |
| Pack | Authored world, characters, knowledge, facts, `when` gates, prose guidance |
| DARPS engine | Context isolation, validation, narrative state, deltas |
| LLM | Classification and narration proposals |


## Entities

Entities are what makes up most of your pack. They are characters, locations, and items.

- Characters: Can be spoken to with /talk and have tracks to gauge their current moods. DARPS will build knowledge graphs for them to emulate what information that character would have access to.
- Locations: Can be examined with /examine and are also passed with /talk so characters are aware of their immediate environment.
- Items: Can be examined with /examine and hold triggers for facts. 'Available items' (such as the player inventory) can be passed with /examine and /talk if you want DARPS to enable various actions with them. 

Read more about entities in [pack authoring](../authoring/index.md).


## Facts, knowledge, and canon

DARPS works around the idea of truth. What is the truth and what is a character's own truth?

- A **fact** is a gated piece of truth the player can learn. Learned facts enter the journal via their `journal_text`.
- The **journal** is an easily-accessible, game-facing object that details learned facts.
- **Knowledge** refers specifically to knowledge a character has innately. It exists on that character's file and is inaccessible to other characters. It may authorize that character to reveal a fact.
- **Shared knowledge** belongs to the entity it describes. DARPS filters the addressee's complete corpus by scope and `when` gates before retrieving relevant entries.
- **Canon** records concrete improvised or host-established details that are not part of the authored fact web. If an LLM makes something up DARPS can optionally record it as canon to maintain coherent storytelling.

For more information see the [Knowledge concept](../concepts/knowledge.md).


## Tracks and persona

**Tracks** are sliding scales that belong to each character that gauge a character's current state of personality.
Tracks can measure anything you like so long as you can design a prompt to measure it. DARPS will use its resolver to gauge a character's reaction to player text. Tracks are defined globally in pack.yaml but a character's specific reaction to that track s defined in the character's file.

For example, you might add a track that measures how much a player is trying to intimidate the character. But each character may react to intimidation differently. At -2 intimidation, one character may be more free with information while another refuses to respond. You can gate information behind tracks so certain information is ONLY possible to attain if a track condition is met. So a track for how much an NPC likes the player is often a good idea.

**Personas** track the player itself in a global way. While tracks gauge a character's disposition, personas gauge the player's disposition. This can help you design game logic to adjust to different play styles. If someone is too aggressive, you could give a helpful hint that sometimes talking is the best method. You can reward good roleplaying, as defined by you.

For more information on tracks, see [Pack Authoring: Characters](../authoring/characters.md) and [Gating with Tracks](../concepts/gates.md#when-gating-with-tracks).


## Gates

Secrets are protected by absence, not merely instruction. Gates prevent designated information ever entering an LLM prompt and most games will use them heavily. Gates come in 3 types:

- `scope`: Implicit gating. Characters have scopes and know all `shared_knowledge` within that scope (unless it is also gated by other conditions).
- `when`: Explicit gating. Information only enters prompts if all the conditions are met. `when` is very flexible and strict.
- `trigger`: Simple options added to items and location interactions that let you broaden the scope of that interaction. For example, you might have a clue that needs the player to check under the rug. The semantic resolver can try and determine if the player attempts this without exact wording but you can help it along with triggers like "lift" "pull" "move".

Gates always belong with the thing they are gating access to so keeping track of them is simpler than if they were defined centrally. For more information on gates, see [the Gates concept](../concepts/gates.md).