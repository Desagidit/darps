# Knowledge

Knowledge is the information DARPS is allowed to place in a character's
briefing when they respond. It is deliberately separate from descriptions,
player discoveries, and global narration.

## The four layers

| Layer | Authored in | Who receives it |
|---|---|---|
| World context | `world.md` | Every response model, including the narrator |
| Shared knowledge | An entity's `shared_knowledge` | Characters holding the entry's scope |
| Individual knowledge | A character's `knowledge` | That character only |
| Narrative memory | Journal and canon state | Later responses according to their normal context |

Use `world.md` for premises every response needs. Use knowledge for information
held by people in the fiction. A location or item's `description` is
examination-grade ground truth and **does not become character knowledge**.
If people should know something from it, author a `shared_knowledge` entry.

## Individual knowledge

Put information unique to a character in their own file:

```yaml
knowledge:
  - content: I locked the west door at ten.
  - content: I heard an argument behind the study door.
    reveals: overheard_argument
    why: I promised not to implicate her Ladyship.
    tell: I become overly precise about the time.
```

`when` conditions decide whether an entry exists in the briefing. A false
condition means the response model never sees the text; this context isolation
is DARPS's primary secrecy guarantee.

## Shared knowledge belongs on its subject

Store shared lore in the file for the thing it describes:

```yaml
# characters/butler.yaml
shared_knowledge:
  - scope: household
    content: Mr. Halloway prepares Sir Edmund's cocoa every evening.
```

The entry is about Halloway, but any eligible household character may know it.
Entity-centric storage keeps one authoritative statement instead of copying it
into ten character files.

## Scopes

Characters subscribe to named scopes:

```yaml
knowledge_scopes: [household, veterans]
```

An omitted entry scope means `common`. Common knowledge is available to every
character by default, but should be used sparingly: it means genuinely
universal knowledge in this fiction. Prefer a named scope for a large but
bounded group.

An exceptional character can opt out without losing named scopes:

```yaml
knowledge_scopes: [household]
common_knowledge: false
```

This suits outsiders, amnesiacs, isolated beings, or other characters who
should not inherit ordinary public knowledge. `common_knowledge` defaults to
`true`.

## How a talk call retrieves knowledge

DARPS uses a secrecy-first pipeline:

```mermaid
flowchart LR
    A["All shared entries"] --> B["Filter by addressee scopes"]
    B --> C["Evaluate conditions"]
    C --> D["Safe corpus"]
    D --> E["Retrieve relevant entries"]
    E --> F["Character briefing and reveal authority"]
```

This order matters. The relevance selector never sees knowledge the addressed
character is not permitted to know.

From the safe corpus, DARPS always includes entries about the addressee, the
current location, and accessible items. It also matches subject names, aliases,
and meaningful words in entry content against the player's message.
Consequently, asking Alice "Who makes the cocoa?" can retrieve Halloway's
household entry even when Halloway is absent and unnamed.

Physical presence is not a knowledge rule. The `/talk` world object therefore
has no `present` field. Characters do not learn facts because someone enters a
room or forget them when that person leaves.

For indirect references or paraphrases, enable:

```yaml
knowledge_resolver: true
```

This makes one additional classifier call per talk turn. It receives only the
already scope- and condition-filtered safe corpus and returns candidate indexes.
DARPS rejects invalid indexes and combines valid selections with deterministic
matches. Leave it off when exact topical matching is sufficient or minimizing
latency is more important.

## Reveals and authority

A `reveals` entry does two things: it briefs the character and grants authority
to propose that fact on that turn. The engine accepts the reveal only if the
entry was actually retrieved and the fact's own gates pass. There is no
separate revealer list to drift out of sync.

## Practical guidance

- Put private memories and secrets in `knowledge`.
- Put group-held information in `shared_knowledge` on its subject.
- Use narrow, meaningful named scopes rather than making everything `common`.
- Write the important topic words directly in `content`; they improve both
  clarity and deterministic retrieval.
- Use `when` for secrecy or story phases, never prompt instructions alone.
- Do not duplicate an entity's `description` into knowledge wholesale. Write
  the coarser fact people plausibly know.
