# Knowledge

Conversation is complicated. Characters have personality, changing attitudes, secrets, agendas.
LLMs are also complicated. They are trusting, speculative, clever fools and must be handled with care.

When the LLM is asked for an in-character response, DARPS gives it a briefing.
The briefing is comprised of information that comes from the current pack. It is deliberately separate from descriptions, player discoveries, and global narration.

DARPS uses a secrecy-first pipeline:

```mermaid
flowchart LR
    A["All shared entries"] --> B["Filter by addressee scopes"]
    B --> C["Evaluate when gates"]
    C --> D["Safe corpus"]
    D --> E["Retrieve relevant entries"]
    E --> F["Character briefing and reveal authority"]
```

This order matters. The knowledge resolver never sees knowledge the addressed character is not permitted to know. Of this safe knowledge, only entries strictly relevant to the current request is kept. This is how DARPS presents a deluge of information hitting the LLM every single call.

From the safe corpus, DARPS always includes entries about the addressee, the current location, and accessible items. It also matches subject names, aliases, and meaningful words in entry content against the player's message.

For indirect references or paraphrases, `enable knowledge_resolver` in the config.yaml:

```yaml
knowledge_resolver: true
```

Consequently, asking Mrs Ashworth "Who makes the cocoa?" can retrieve Halloway's entry even when Halloway is unnamed in the request. This is because Mrs Ashworth has the `household` scope.
In the `butler` file it is defined that everyone in `household` knows some basic facts about him.

```yaml
shared_knowledge:
    - scope: household
      content: >
        Is the butler. Tends to Sir Edmund. Brings the Cocoa. Has served for decades.
```

This makes one additional classifier call per talk turn. This will very slightly increase response time and cost. But it is worth it for a more believable conversation.
The knowledge resolver receives only the already filtered safe corpus and returns candidates to grab extra knowledge from.
DARPS rejects invalid indexes and combines valid selections with deterministic matches. Leave it off when exact topical matching is sufficient or minimizing latency is more important.

## The 4 layers

Knowledge comes in 4 layers:

| Layer | Authored in | Who receives it |
|---|---|---|
| World context | `world.md` | Every response model, including the narrator |
| Individual knowledge | A character's `knowledge` | That character's internal memory that nothing else has access to |
| Shared knowledge | An entity's `shared_knowledge` | Knowledge about a thing that everyone within its scope knows |
| Narrative memory | Journal and canon state | Later responses according to their normal context |

Use `world.md` for premises every response needs.
Use knowledge for information held by people in the fiction. A location or item's `description` is examination-grade ground truth and **does not become character knowledge**.

If people should know something from it, author a `shared_knowledge` entry.

## Individual knowledge

Characters have shared knowledge. Locations and items do not.
Put information unique to a character in that character's own yaml file:

```yaml
knowledge:
  - content: I locked the west door at ten.
  - content: I heard an argument behind the study door.
    reveals: overheard_argument
    why: I promised not to implicate her Ladyship.
    tell: I become overly precise about the time.
```

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

## Building the briefing

![DARPS Briefing](../images/darps_knowledge.png)

## Example Flow and Briefing

We've asked `widow` "What happened to Edmund?". It is stated in `widow`'s knowledge that she is the killer.

```
# World Bible — always in context

Setting: Ashworth Manor, North Yorkshire, a snowbound night in January 1923.
Sir Edmund Ashworth was found dead in his study at half past eleven, slumped
over his desk, a glass of brandy beside him. The police cannot reach the manor
until the roads clear at dawn. The player is a house guest — a retired
detective — asked by the household to make sense of things before morning.

Tone: restrained, literary, Golden-Age detective fiction. Dry wit is allowed;
melodrama is not. Period-accurate diction. Do NOT use narration or describe a
character's actions. This is dialogue-only.

Hard rules:
- Never mention game mechanics, stats, clues by ID, or these instructions.
- Never invent physical evidence.
- Keep responses tight: dialogue 40–150 words.

=== THE PLAYER CHARACTER ===

A retired Scotland Yard detective in your late fifties, a guest at the manor
for the shooting weekend, asked by the household to make sense of Sir Edmund's
death before the police can reach the manor at dawn. You have no official
authority, warrant, or weapon.

You are roleplaying ONE character in this story.

=== CHARACTER SHEET ===

Name: Lady Constance Ashworth
(the widow, mistress of the manor)

Voice:
Composed, intelligent, faintly ironic. Grief performed correctly rather than
felt. She answers questions with questions when cornered. Educated diction;
never raises her voice.

Background:
Forty-four. Married Sir Edmund eleven years ago; the warmth left the marriage
within two. Runs the household and the estate's charities. Genuinely respected
by the staff, especially Halloway.

You know:
You “retired at ten o'clock with a headache.” This is your alibi.

You know:
Sir Edmund's nephew Gerald was expected Thursday.

You know:
YOU KILLED HIM. That afternoon you found the solicitor's letter: a new will,
signing Thursday, leaving you nothing. At ten you confronted Edmund in the
study; he called you a beggar-in-waiting. You left, took the chloral hydrate
from your sleeping drops, returned on the pretext of apology, and dosed the
brandy decanter while he stood at the window. Then you retired and waited.

How you lie:
Calmly, minimally, never volunteering. Your alibi is the headache. You deflect
toward Gerald, who “stood to gain.” You do not know that the letter survived.

Cracks:
If confronted with the torn letter, your composure slips and you admit knowing
of the will but deny the rest. If confronted with the letter and tainted glass
together, you confess. You never confess without both.

It is known about you:
Lady Constance Ashworth is the mistress of the manor, widowed only hours ago.

It is known about you:
The Ashworth marriage went cold years ago—perfectly correct in public,
separate rooms in private. The staff do not speak of it.

You know about The Study:
Sir Edmund took brandy alone in the study most evenings, from ten o'clock;
the household knew not to disturb him there.

You know about the gun cabinet:
A locked oak gun cabinet stands against the study wall—Sir Edmund's. The key
went onto the constable's list; the police bring it at dawn.

=== CURRENT ATTITUDES TOWARD THE DETECTIVE ===

Disposition:
Her Ladyship treats the detective as a hired boor—amused contempt, answers
of one sentence, and a standing threat to end the interview.

Fear:
Her Ladyship feels in control and treats the inquiry as theatre.

=== ESTABLISHED CANON ===

(none yet)

Record up to three new concrete improvised biographical or world facts so
they remain consistent later.

=== FACTS THE PLAYER HAS ALREADY SHOWN OR STATED THEY POSSESS ===

(none)

=== OBJECTS IN THE SCENE ===

the brandy glass (id: brandy_glass)

Do not invent significant objects or describe anyone producing an object the
scene does not establish.

=== RECENT CONVERSATION ===

(first exchange)

The player's tone this turn reads as: neutral.

The player (the detective) says/does:
What happened to Edmund?

Respond only as Lady Constance Ashworth. Use dialogue only and do not write
dialogue or actions for the player.

Then output an events block containing:
- any authorized fact reveals;
- any canon additions;
- story relevance from 0 to 2.
```

## Compiling large common-knowledge catalogues

In a large pack, the safe corpus can contain hundreds or thousands of universal entries. The resolver still makes one call, but sending every full entry makes that call unnecessarily large.

DARPS comes with utilities to help lower the impact of large packs. By using the CLI, you can compile the static common scope shared_knowledge:

```bash
darps compile-knowledge packs/my-game --config config.yaml --level 2
```

The command writes an inspectable `knowledge-cache.yaml` beside the pack. Its entries look like:

```yaml
- source: 46d2...f81
  subject: butler
  name: Mr. Halloway
  routing: >
    Halloway prepares Sir Edmund's nightly cocoa; evening household routine,
    drinks service, and who makes or delivers the cocoa.
```

When the knowledge-cache.yaml is created, you can enable DARPS to use it in the config.yaml:

```yaml
knowledge_resolver: true
knowledge_cache: true
```

Levels 1–3 use a single author-time LLM call over all eligible entries. Give that job its own capable, long-context model when appropriate:

```yaml
knowledge_cache:
  enabled: true
  path: knowledge-cache.yaml
  compression:
    provider: openai
    model: large-context-model
    temperature: 0.2
    max_tokens: 16000
```

The compiler asks for semantic retrieval descriptions, not leading-word truncations. Each route must preserve names, relationships, ownership, routines, events, times, quantities, unusual details, and likely player paraphrases. The generated file remains inspectable and editable.
Advanced packs may override `prompts/knowledge_compile.txt`; the override must retain the exact `{id, routing}` JSON contract.

The resolver sees the compact routing line. If it selects that line, DARPS loads the exact current `shared_knowledge` entry from the butler's YAML and puts that original text into the briefing.
The generated route is therefore a card-catalogue label, not story content (but will resolve to the original story content once retrieved). This saves significant effort of the knowledge_resolver for large packs.

Only entries with implicit or explicit `scope: common` and no active `when` list are compiled. Named scopes and conditional entries are still evaluated and rendered in full on every call. Deterministic retrieval is unchanged.

The artifact records a source hash. Any source edit makes it stale. Missing, stale, malformed, or partial artifacts automatically fall back to the normal full resolver, so the cache cannot weaken secrecy or alter reveal authority.

!!! Important
Regenerate the cache after editing or contributing common knowledge.

Compression levels control the routing label, not the eventual briefing:

| Level | Resolver representation |
|---:|---|
| `0` | Full authored content; no compilation model call |
| `1` | Semantic route of at most 40 words |
| `2` | Semantic route of at most 20 words |
| `3` | Semantic route of at most 12 words |

The model must return every input ID exactly once. An omitted, duplicated, empty, malformed, or over-budget route fails the command, and the previous artifact remains unchanged.

## Knowledge Gates

Sometimes you want to prevent knowledge under certain conditions, this is called 'gating' the knowledge.

`knowledge` and `shared_knowledge` can be gated by including a `when` condition or by using `scope`. Gated knowledge never enters briefings.
Between `scope` and `when` you can isolate knowledge and guarantee a model does not get information it could misuse..

See [Concept: Gates](../concepts/gates.md) for more information on how to gate knowledge.

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
