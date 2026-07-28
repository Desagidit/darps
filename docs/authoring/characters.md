# Characters

Character files define the NPC characters in your game. In this article we'll go through how to write a character file and what the fields mean.

Character files combine identity, performance guidance, private knowledge, shared reputation, and per-character attitude behavior.

??? Expand character yaml example
	```yaml
	--8<-- "docs/examples/minimal-pack/characters/mira.yaml"
	```

| Field | Purpose |
|---|---|
| `id` | Stable API and reference identifier |
| `name` | Display name |
| `summary` | Concise role description |
| `aliases` | Names players are likely to use |
| `voice` | Speech rhythm, vocabulary, and mannerisms |
| `background` | Biography that prevents contradictory improvisation |
| `knowledge_scopes` | Named shared-knowledge scopes this character receives |
| `common_knowledge` | `false` opts out of implicit common-scope knowledge |
| `knowledge` | Individual knowledge, optionally gated or revealing facts |
| `shared_knowledge` | What others know about this character |
| `track_settings` | Starting values, optional speed overrides, and supplemental guidance |
| `track_prose` | Behavioral text selected from current track values |
| `hints` | `false` prevents this character delivering pacing hints |


## Basic data

Every character has some basic information.

* `id`: A unique DARPS ID for this character that will be used internally. You should ensure your game understands what each character's ID is so you can call DARPS to speak to individuals.
* `name`: The character's canonical name that DARPS will preferentially use
* `summary`: A simple summary for the LLM to understand the character. Keep it short.
* `aliases`: Alternate names used by the resolver to help map mentions. You might want to include forenames, nicknames, familial relationships, job titles and so on.
* `background`: A longer form description of the character. This has some redundancy with `summary` but it can help the LLM to have both.
* `knowledge_scopes`: Which scopes this character belongs to. It knows everything within this scope. Consider groups of knowledge. Who are family? Who belong to the household? Who are strangers? Who are expects in a particular subject? Who are accomplices?
* `hints`: If `true` DARPS can allow this character to deliver pacing hints. For more information, see [Concept: Hints](../concepts/hints.md).


## Knowledge

*To understand how DARPS uses Knowledge, see [Concept: Knowledge](../concepts/knowledge.md).*

Character `knowledge` defines what that character knows internally. It is not available to other characters (they are not psychic) and is used in all conversation with this character, provided it isn't gated knowledge.
Knowledge block entries are:

| Field | Engine behaviour |
|---|---|
| `content` | Prose placed in the briefing. |
| `when` | Deterministically controls whether the entry enters the briefing. See [Gates](../concepts/gates.md) for more information. |
| `reveals` | Links the entry to an engine-validated fact disclosure. See [Facts](../authoring/facts.md) for more information. |
| `why` | Rendered as concealment guidance on a revealing entry. |
| `tell` | Rendered as a behavioural tell on a revealing entry. |

```yaml
- content: The missing clock was booked in on Tuesday.
```

A concealed testimony entry connects knowledge to a fact:

```yaml
- content: The clock arrived after closing.
  reveals: late_delivery
  why: Admitting it would expose an insurance violation.
  tell: She becomes exacting whenever the arrival time is mentioned.
```

`why` and `tell` shape concealment. They do **not** provide security. They are **not** gates.

Anything else is just included as prose, despite how yaml syntax highlighting might make it appear.

```
knowledge:
  - content: "She 'retired at ten o'clock with a headache' (this is her alibi)."
  - content: "Sir Edmund's nephew Gerald was expected Thursday."
  # Conditional knowledge: enters context ONLY when the engine's ground truth
  # names this character the culprit. One file serves every future variant.
  - content: >
      YOU KILLED HIM. That afternoon you found the solicitor's letter: a new
      will, signing Thursday, leaving you nothing.
	  
      How you lie: calmly, minimally, never volunteering. Your alibi is the
      headache. You deflect toward the nephew Gerald, who "stood to gain."
```

In this case "How you lie" is not a special field, although your syntax highlighting may suggest otherwise.


## Shared Knowledge

*To understand how DARPS uses Shared Knowledge, see [Concept: Knowledge](../concepts/knowledge.md).*

Character `shared_knowledge` is what other characters know ABOUT this character. You will likely spend a lot of time writing `shared_knowledge` as it gives your game a level of rich realism that few other systems can match.

`shared_knowledge` with no scope defined is "common" and known by all characters. By default, every character belongs to the common scope.
There may be niche circumstances where you'd want to opt out of the common scope (characters with amnesia, for example). Characters can opt out of the common scope with:

```
common_knowledge: false
```

Shared Knowledge block entries are:

| Field | Engine behaviour |
|---|---|
| `content` | Prose placed in the briefing. |
| `when` | Deterministically controls whether the entry enters the briefing. See [Gates](../concepts/gates.md) for more information. |
| `reveals` | Links the entry to an engine-validated fact disclosure. See [Facts](../authoring/facts.md) for more information. |
| `why` | Rendered as concealment guidance on a revealing entry. |
| `tell` | Rendered as a behavioural tell on a revealing entry. |
| `scope` | For `shared_knowledge`; controls which characters can receive it. |

While `shared_knowledge` works identically to `knowledge` in terms of its fields, they are distinct concepts. Think of `shared_knowledge` as a venn diagram of information that each character takes its own position in.
You might decide everyone in the household knows who the butler is so you place this in the butler's file:

```
shared_knowledge:
    - scope: household
      content: >
        Is the butler. Tends to Sir Edmund. Brings the Cocoa. Has served for decades.
```

And ensure all the household characters have the `household` scope. Strangers might not know him.

```
shared_knowledge:
    - scope: household
      content: >
        Is the butler. Tends to Sir Edmund. Brings the Cocoa. Has served for decades.
    - scope: family
      content: >
        He has served for decades but remains enigmatic. Loyal and trustworthy. He never drinks the cocoa himself.
```

Meanwhile the heads of the household might have information that houseguests do not, so we can build knowledge of the Butler in increasing complexity.

```
shared_knowledge:
    - scope: household
      content: >
        Is the butler. Tends to Sir Edmund. Brings the Cocoa. Has served for decades.
    - scope: family
      content: >
        He has served for decades but remains enigmatic. Loyal and trustworthy. He never drinks the cocoa himself.
	- scope: guest
	  content: >
		He's distant and unsettling. Almost rude.
```

Meanwhile the same character is seen quite differently to people who don't yet understand him.

You can also [gate](../concepts/gates.md) shared_knowledge, which prevents any character in that scope knowing it until you choose otherwise.
Perhaps you intend for the player to falsley accuse the Butler halfway through the story after being fed some tricky information. In the second half of the story they might uncover their mistake but in the mean time, all the characters are convinced the Butler did it:

```
shared_knowledge:
    - scope: household
      content: >
        The Butler murdered Edmund. I can't believe it but the evidense points to him.
      when:
        - fact_learned: blamed_butler
	    - not:
          fact_learned: disclosed_alibi
```

In the example above, everyone in the household will think the Butler did it after you blame him. But disclosing an alibi later will absolve him.

`shared_knowledge` is a powerful tool to keep characters acting consistently and affect changes at scale in your game.


## Tracks

Tracks are sliding scales that you can use to judge how characters currently feel.

| Location | Responsibility |
|---|---|
| `pack.yaml → tracks` | Declares which tracks exist, their bounds, starting values, normal speeds, and baseline adjudication rules |
| Character `track_settings` | Overrides any shared field for this character |
| Character `track_prose` | Describes how the current value affects that character’s behaviour |

Tracks are defined globally in pack.yaml:

```
tracks:
  disposition:
    min: -3
    max: 3
    start: 0
    speed: 0.5
    guidance: >-
      Patience, discretion, and useful evidence raise disposition. Insults, accusations without evidence, and threats lower it. Routine questions and repeated pleasantries do not change it.
default_track: disposition
```

- `min` and `max` clamp the possible values of the track and the actual value can be anything inbetween
- `start` the default starting value for the track
- `speed` is the positive scaling factor used by every character unless they override it.
- `guidance` defines the shared rules for judging the track.

In this example, we have a fairly generic 'disposition' track and define how the LLM should judge it. It doesn't say how a character reacts to disposition because that belongs in the character files.
Now that it's defined, every character inherits it. In the Widow's character file, `widow.yaml`:

```
track_settings:
  disposition:
    min: -3
    max: 2      # she will cooperate, but never become wholly trusting
    start: -1.0   # defensive beneath impeccable social form
    speed: 0.35   # deliberately difficult to sway
    guidance: >
      Sympathy and social grace alone leave her unchanged. Intelligent,
      evidence-backed restraint impresses and unsettles her more than kindness
      or aggression, which she meets with icy amusement.

track_prose:
  disposition:
    "-2": >
      Her Ladyship treats the detective as a hired boor — amused contempt,
      answers of one sentence, and a standing threat to end the interview.
    "0": >
      Her Ladyship is the gracious, grieving hostess — cooperative in form,
      empty in substance.
    "1": >
      Her Ladyship finds the detective almost worth talking to. The irony
      softens; the answers lengthen; the watchfulness does not.
```

Note that `track_settings` in the character file is identical in form to the track definition. You do not have to supply any track_settings and may skip any setting within it. Any provided setting will override the pack.yaml's value with the character's value, except guidance which adds to the pack's guidance.

`track_prose` defines how the character's dialogue changes according to different stages of the track. `track_prose` keys are numeric thresholds stored as YAML strings. DARPS selects the highest threshold not exceeding the current value and supplies only that prose to the character model.

Tracks can also be used [as gates](../concepts/gates.md#when-gating-with-tracks).
