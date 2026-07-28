# Hints

Hints are an optional, session-wide pacing system to help your game run smoothly. With such a high amount of freedom, it's easy for your players to get lost. Hints encourage characters or the narrator to steer a stuck player toward an undiscovered fact without automatically giving that fact away.

Hints is a global setting and can only have one style. It is a coarsegrain system designed for overall game feel, not one specific sticking point.

Enable them in the host’s config.yaml:

```
hints:
  after_turns: 6
  style: subtle
```

Or globally disable them (this is default if the option is omitted):

```
hints: false
```

Available styles are:

| Style | Character behaviour | Examination narration |
|---|---|---|
| `subtle` | Makes an authored behavioural tell more noticeable | Briefly draws attention toward the relevant place |
| `pointed` | Steers the conversation toward the withheld subject | Gives the relevant area a conspicuous sensory detail |
| `forthcoming` | May volunteer information given a plausible opening; relaxes eligible `track_gte` fact gates by 1 | Strongly directs the player toward where they should investigate |


Note that `forthcoming` is the only one that alters how DARPS works on a deterministic level. The others just push the LLM response to be more generous.


## How DARPS decides the player is stuck

DARPS persists a global fruitless_turns counter. After every `/talk` or `/examine` request:

- If the player learns a new fact, the counter resets to 0.
- If no fact is learned and the response reports story_relevance of 1 or 2, the counter increases by one.
- Irrelevant exchanges with story_relevance: 0 do not increase or reset it.

Guardrail/meta responses do not increase it.
Track changes, persona changes, and new canon do not count as progress.

`/grant_fact` also resets the counter when it grants a new fact.
`/narrate` is display-only and does not affect hint pacing.

The response LLM reports `story_relevance` in its hidden events block. DARPS validates it as an integer from 0 to 2.
With `after_turns: 6`, the sixth qualifying fruitless exchange leaves the counter at six. The hint instruction therefore enters the prompt for the next request—the seventh exchange.


## Choosing a hint

For /talk, DARPS looks at facts the addressed character is authorized to reveal through their currently loaded knowledge. It chooses an undiscovered candidate whose prerequisites have been learned.
For /examine, it looks through the resolved item or location’s examine_reveals rules for an undiscovered fact whose when gate and fact gates currently pass. The rule’s where field provides the wording used to direct the narrator:

```
examine_reveals:
- reveals: torn_letter
  where: the desk drawers and their papers
```

Once selected, DARPS adds a private pacing instruction to the character or narrator prompt. There is no separate hint response or API event—the hint simply influences the returned prose.


## Important limitations

Hints are primarily LLM guidance, so subtle and pointed do not deterministically force a particular line. They also never authorize a fact that the character does not know or that the examined entity cannot reveal.
`forthcoming` has one mechanical concession for character disclosures: it supplies one point of slack to the fact’s `track_gte` gate. For example:

```
when:
- track_gte:
    track: disposition
    value: 2
```

This can be treated as requiring 1 while a forthcoming character hint is active. Other gates, prerequisites, and reveal authority still apply. The counter is global to the session — **not** per character or location — and remains at or above the threshold until a new fact is learned. Consequently, DARPS can continue supplying hints on later eligible turns.

Individual entities can opt out:

```
hints: false
```

This can be placed on a character, item, or location. Omitting hints permits that entity to participate. Omitting the top-level hints configuration entirely disables the system.