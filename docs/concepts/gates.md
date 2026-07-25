# Gates

Sometimes you want to prevent information under certain conditions, this is called 'gating' the information.

These are the types of gated information:

| Content | Gating fields | Effect |
|---|---|---|
| Character `knowledge` | `when` | Controls whether private knowledge enters that character’s briefing |
| Entity `shared_knowledge` | `when` plus `scope` | Controls whether shared knowledge enters the safe retrieval corpus |
| Facts | `requires` and `when` | Controls whether the fact can enter the journal |
| Location or item `examine_reveals` | optional `triggers`, plus `when` | Optionally matches a specific detail, then checks whether this discovery source is active |

`knowledge` and `shared_knowledge` can be gated by including a `when` condition. Gated knowledge never enters briefings.
Between `scope` and `when` you can isolate knowledge and guarantee a model does not get information it could misuse.


## Scope

Scopes are simple ways to declare groups of knowledge.
To avoid having to repeat this information across multiple files, you can give it a scope. If the knowledge has `household` scope then it is only known by characters with `household` scope, regardless of the file that knowledge sits in.

Think of scopes as a venn diagram of knowledge. A chef might have the scopes `[household, kitchen, trusted]`. The `household` scope might know there's a walk-in freezer in the kitchen, but only `kitchen` scope knows the door lock is broken.

```
id: butler
name: Mr. Halloway
summary: the butler, thirty years in service
aliases: [Halloway, Mr Halloway, the butler]
knowledge_scopes: [household]

voice: >
  Formal, precise, unfailingly courteous even when evasive. Long pauses. Refers to the dead man as "Sir Edmund" and the widow as "her Ladyship." Never uses slang. When uncomfortable, he polishes something.

background: >
  Sixty-one. Entered service at Ashworth Manor under Sir Edmund's father. A widower himself; his late wife was the manor's cook. No children. Considers the household's dignity his personal responsibility. Privately fond of her Ladyship, whom he has watched endure a cold marriage.

shared_knowledge:
    - scope: household
      content: >
        Is the butler. Tends to Sir Edmund. Brings the Cocoa. Has served for decades.
```

Note how we've infodumped extremely basic household information about the butler into the `household` scope. Now everyone in `household` knows this about him but a stranger without that scope would not.

## When

`when` is a simple keyword that allows strict, conditional gating on
`knowledge`, `shared_knowledge`, `facts`, and `examine_reveals`.

Learning to use `when` flexibly is extremely important to building complex worlds.

For discovery rules, source-level and fact-level gates serve different purposes:

- `examine_reveals[].triggers`, on either a location or item, optionally
  requires the player's words to identify a relevant detail. With no triggers,
  a general examination is enough.
- `examine_reveals[].when` controls whether that particular discovery route
  is active.
- A fact's `requires` and `when` apply to every route that could reveal it.

For example, a cellar search can require light without preventing a character from revealing the same fact through testimony:

```yaml
examine_reveals:
  - reveals: muddy_footprints
    where: beneath the cellar window
    triggers:
      - window
      - floor
      - mud
    when:
      - flag: cellar_lit
```

`when` may itself check previously learned facts:

```yaml
when:
  - fact_learned: cellar_key
```

### when: gating with Flags

The simplest gate is using flags. Flags are entirely host-owned and are not declared in, or managed by, DARPS. They are (optionally) passed by the game in the [/talk call](../api/http-reference.md#post-talk). These are good for when certain knowledge relies on binary game state changes.

```
knowledge:
  - content: >
      The cellar door is now open. You may discuss what is inside.
    when:
      - {flag: cellar_open}
```

You can check for negative flags as well.

```
knowledge:
  - content: >
      You insist the cellar has been sealed for years.
    when:
      - {not: {flag: cellar_open}}
```

### when: gating with Facts

Similar to Flags, Facts check if a binary condition is met. Flags are best used when the thing you want to check against relies on analysing character dialogue or examining pack items/locations.

```
knowledge:
  - content: >
      The player has found the torn letter. You can no longer deny knowing
      about the new will.
    when:
      - {fact_learned: torn_letter}
```

### when: gating with Variables

Packs have variables declared in vars.yaml. These are generally used to swap around key game details. For example, if you wanted to quickly change who the culprit is. Or who holds a key item.
In these cases, vars can be tested against as key-value pairs. Be aware that `self` can be used if that var holds the entity ID in question.

```
shared_knowledge:
  - scope: household
    content: Her sleeping medicine went missing shortly before the murder.
    when:
      - {var: culprit, is: self}
```

### when: gating with Tracks

Sometimes people won't give up knowledge unless they're scared or trust you. You can define any number of character tracks to gauge how that character is feeling or progressing.

```
knowledge:
  - content: >
      You now trust the player enough to admit that you saw Lady Ashworth
      enter the study.
    when:
      - track_gte:
          track: disposition
          value: 1
```

By default, the tracks refer to `self` which means it'll check against the entity to which the file belongs.
It's possible to gate using the track of a different entity altogether. This is useful for `shared_knowledge`.

```
shared_knowledge:
  - scope: household
    content: >
      Halloway has begun privately telling trusted investigators about the argument.
    when:
      - track_gte:
          track: disposition
          of: butler
          value: 1
```

### when: Combining gates

You can mix and match your gates to lock knowledge behind more complex requirements.

```
knowledge:
  - content: >
      You are prepared to explain what happened in the cellar.
    when:
      - {flag: cellar_open}
      - {fact_learned: muddy_footprints}
      - track_gte:
          track: disposition
          value: 1.5
```

## Triggers

`triggers` are an optional textual gate on an `examine_reveals` rule. They answer:

> Did this examination mention the part, property, or action needed to find this particular thing?

They can be used on both locations and items:

```yaml
examine_reveals:
  - reveals: bitter_glass
    where: the syrupy dregs at the bottom of the glass
    triggers:
      - dregs
      - smell
      - taste
```

After resolving the examination target, DARPS checks the player's target and message for the trigger terms. Matching is case-insensitive, and any one trigger is sufficient. In this example, examining the glass while saying "smell the dregs" can activate the source; merely looking at its engraving cannot. General classifier topic words are not used as trigger matches.

For semantic matching of paraphrases and synonyms, enable the optional resolver:

```yaml
examine_resolver: true
```

The resolver receives only the already-resolved entity's currently eligible trigger groups. It does not see fact IDs, journal text, inactive rules, or other entities. It returns candidate indexes, which DARPS validates and adds to deterministic matches. It cannot remove a direct match or authorize a fact whose source or fact gates are closed. This adds at most one classifier call per examination and is skipped when no unmatched trigger groups remain.

For example, a resolver can recognize that "sniff what remains" qualifies a group containing `dregs`, `smell`, and `odour` even if none of those exact words appeared. Without `examine_resolver`, authors should list the common synonyms they expect players to use.

Triggers are optional. If `triggers` is omitted or empty, examining the entity generally is sufficient:

```yaml
examine_reveals:
  - reveals: cracked_handle
```

This is useful for obvious discoveries or for locations where casting a general gaze around the room should reveal something.

### Triggers compared with `when`

Triggers inspect the current examination's language. `when` inspects established game and narrative state:

```yaml
examine_reveals:
  - reveals: hidden_message
    triggers:
      - writing
      - ink
      - message
    when:
      - flag: ultraviolet_lamp_on
```

Here both gates must pass:

1. The player must examine the relevant detail by matching a trigger.
2. The host must report that the ultraviolet lamp is on.
3. The linked fact's own `requires` and `when` gates must also pass.

Use triggers for questions such as “did the player inspect the lock?” or “did they smell the drink?” Use `when` for questions such as “is the cabinet open?”, “has another fact been learned?”, or “is this character sufficiently cooperative?”

### Triggers compared with scope

`scope` applies only to `shared_knowledge`. It decides which characters are eligible to know an entry:

```yaml
shared_knowledge:
  - scope: household
    content: The butler prepares Sir Edmund's cocoa every evening.
```

It does not inspect player language and does not authorize physical discoveries. A character either holds the required knowledge scope or does not. After scope filtering, a shared-knowledge entry's own `when` gates are checked, and relevant safe entries may then enter that character's briefing.

In short:

| Mechanism | Main question | Used on |
|---|---|---|
| `scope` | Who is eligible to know this? | `shared_knowledge` |
| `when` | Is this content active in the current state? | Knowledge, shared knowledge, facts, and examination rules |
| `triggers` | Did this examination mention the necessary detail or action? | `examine_reveals` |

These mechanisms are cumulative, not alternatives. Use each only for the question it answers.

Triggers are also distinct from entity `aliases`. Aliases identify which item or location the host targeted; triggers decide which discovery rule on that already-resolved entity can activate. For example, `snifter` may be an alias that resolves the brandy glass, while `smell` is a trigger for discovering what is in its dregs.
