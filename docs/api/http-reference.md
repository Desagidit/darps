# HTTP API reference

DARPS runs as a local JSON-over-HTTP service. A host game creates a session,
sends conversation or examination requests, reads validated narrative deltas,
and stores the session state in its own save system.

All request and response bodies are JSON objects unless an endpoint explicitly
uses Server-Sent Events (SSE).

## Health and metadata

These endpoints let a host wait for DARPS to become ready and inspect the
loaded pack without exposing story secrets. Neither endpoint needs a session.

### `GET /health`

Check whether the DARPS process is ready to receive requests.

**Parameters:** None.

**Returns — `200 OK`**

```json
{
  "status": "ok",
  "pack": "Workshop Ledger"
}
```

| Field | Type | Meaning |
|---|---|---|
| `status` | String | `ok` when the server is ready. |
| `pack` | String | Display name of the loaded pack. |

### `GET /pack`

Read secret-safe metadata for building menus, validating host IDs, and
discovering supported mechanics.

**Parameters:** None.

**Returns — `200 OK`**

```json
{
  "pack_id": "workshop-ledger",
  "name": "Workshop Ledger",
  "characters": [
    {"id": "mira", "name": "Mira Vale", "aliases": ["the keeper"]}
  ],
  "locations": [
    {"id": "workshop", "name": "The Workshop", "aliases": ["work room"]}
  ],
  "items": [
    {"id": "ledger", "name": "the delivery ledger", "aliases": ["book"]}
  ],
  "tracks": {
    "disposition": {"min": -3, "max": 3, "start": 0, "speed": 0.5}
  },
  "default_track": "disposition",
  "persona": {
    "careful_investigator": {"min": -3, "max": 3, "default": 0, "speed": 0.25}
  },
  "capabilities": [
    "talk",
    "talk_stream",
    "examine",
    "examine_stream",
    "narrate",
    "narrate_stream",
    "tracks",
    "persona",
    "journal",
    "canon"
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `pack_id` | String | Stable save/API identifier derived from the pack name. |
| `name` | String | Pack display name. |
| `characters` | Array of entity objects | Public character identity data. |
| `locations` | Array of entity objects | Public location identity data. |
| `items` | Array of entity objects | Public item identity data. |
| `tracks` | Object | Numeric track definitions keyed by track ID. |
| `default_track` | String or null | Track used when `/adjust_track` omits `track`. |
| `persona` | Object | Numeric persona definitions keyed by dimension ID. |
| `capabilities` | Array of strings | Features exposed by this server. |

Each entity object contains:

| Field | Type | Meaning |
|---|---|---|
| `id` | String | Canonical ID used by API requests. |
| `name` | String | Player-facing display name. |
| `aliases` | Array of strings, optional | Alternate matching terms authored in the pack. |

Each track definition may contain:

| Field | Type | Meaning |
|---|---|---|
| `min` | Number | Lowest permitted value. |
| `max` | Number | Highest permitted value. |
| `start` | Number | Pack-wide starting value, inherited unless the character overrides it. |
| `speed` | Number, optional | Pack-wide rate applied to classifier-adjudicated track shifts. |

Each persona definition may contain:

| Field | Type | Meaning |
|---|---|---|
| `min` | Number | Lowest permitted value. |
| `max` | Number | Highest permitted value. |
| `default` | Number | Initial session-wide value. |
| `speed` | Number, optional | Rate applied to classifier-adjudicated persona shifts. |

`GET /pack` never returns facts, descriptions, variables, knowledge, authored
gates, summaries, or prompt guidance.

## Sessions and state

A session is one in-memory playthrough. DARPS serializes requests within each
session, but the host owns persistence: retrieve `/state`, store it in a save
slot, and restore it later with `POST /session` or `POST /state`.

### `POST /session`

Create a new session or restore a saved state into a new session.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | No | String | Explicit session ID. Omit it to receive a generated ID. The ID must not already be active. |
| `state` | No | State object | Saved DARPS state to validate and restore. Omit it to start a fresh session. |

Create a fresh session:

```json
{}
```

Restore a save under an explicit ID:

```json
{
  "session": "save-slot-1",
  "state": {
    "state_version": 1,
    "pack_id": "workshop-ledger",
    "turn": 12,
    "facts_learned": ["altered_ledger"]
  }
}
```

**Returns — `200 OK`**

```json
{
  "session": "save-slot-1",
  "state": {
    "state_version": 1,
    "pack_id": "workshop-ledger",
    "turn": 12,
    "facts_learned": ["altered_ledger"],
    "tracks": {"disposition": {"mira": -0.5}},
    "canon": [],
    "conversations": {},
    "fruitless_turns": 0,
    "persona": {"careful_investigator": 0},
    "persona_history": []
  }
}
```

`state` is the complete normalized state, including defaults for optional
fields omitted from the supplied save. An incompatible state returns
`400 invalid_state`; an active explicit session ID returns
`409 session_conflict`.

### `POST /session/close`

Remove an active session from server memory.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Session ID to close. |

```json
{"session": "save-slot-1"}
```

**Returns — `200 OK`**

```json
{"closed": "save-slot-1"}
```

Closing a session does not delete a save owned by the host. Closing an ID that
is no longer active is harmless.

### `GET /state`

Retrieve the complete state object for saving.

**Query parameters**

| Parameter | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |

```http
GET /state?session=save-slot-1
```

**Returns — `200 OK`**

```json
{
  "session": "save-slot-1",
  "state": {
    "state_version": 1,
    "pack_id": "workshop-ledger",
    "turn": 12,
    "facts_learned": ["altered_ledger"],
    "tracks": {"disposition": {"mira": 0.5}},
    "canon": [],
    "conversations": {
      "mira": [
        {"player": "Who changed this entry?", "reply": "I could not say."}
      ]
    },
    "fruitless_turns": 1,
    "persona": {"careful_investigator": 0.25},
    "persona_history": [
      {"kind": "examine", "input": "Compare the ink."}
    ]
  }
}
```

### `POST /state`

Replace an active session's state with a validated save.

Use this when the host wants to load into an existing session ID. To create a
new session and restore in one request, use `POST /session`.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session whose state will be replaced. |
| `state` | Yes | State object | Saved state to validate and normalize. |

```json
{
  "session": "save-slot-1",
  "state": {
    "state_version": 1,
    "pack_id": "workshop-ledger",
    "turn": 12,
    "facts_learned": ["altered_ledger"]
  }
}
```

**Returns — `200 OK`**

```json
{
  "session": "save-slot-1",
  "state": {
    "state_version": 1,
    "pack_id": "workshop-ledger",
    "turn": 12,
    "facts_learned": ["altered_ledger"],
    "tracks": {"disposition": {"mira": -0.5}},
    "canon": [],
    "conversations": {},
    "fruitless_turns": 0,
    "persona": {"careful_investigator": 0},
    "persona_history": []
  }
}
```

The replacement is normalized in the same way as `POST /session`: missing
narrative fields receive defaults, numeric tracks/persona are clamped, and
unknown entity IDs are rejected.

### The state object

The state object is DARPS-owned narrative memory. It deliberately excludes
host-owned location, inventory/accessibility, and flags.

| Field | Required when restoring? | Type | Meaning |
|---|---:|---|---|
| `state_version` | Yes | Integer | State schema version. It must match the running engine. |
| `pack_id` | Yes | String | Pack identity. It must match the pack loaded by this server. |
| `turn` | No | Non-negative integer | Number of talk/examine requests that entered turn processing. Defaults to `0`. |
| `facts_learned` | No | Array of fact ID strings | Ordered journal facts already learned. Unknown IDs are rejected. |
| `tracks` | No | Object | Track values keyed first by track ID, then character ID. |
| `canon` | No | Array of strings | Accepted improvised or host-added narrative truths. |
| `conversations` | No | Object | Recent conversation history keyed by character ID. |
| `fruitless_turns` | No | Non-negative integer | Relevant turns without a new fact; used for hint pacing. |
| `persona` | No | Object | Persona values keyed by dimension ID. |
| `persona_history` | No | Array of persona-history objects | Recent player inputs used for persona consistency. |

The nested `tracks` object has this shape:

```json
{
  "disposition": {
    "mira": 0.5,
    "tom": -1.0
  }
}
```

Track IDs and character IDs must exist in the loaded pack. Values must be
numbers and are clamped to the track's current bounds.

The nested `persona` object maps each declared dimension ID to its current
numeric value:

```json
{"careful_investigator": 0.25}
```

Unknown dimension IDs are rejected, and values are clamped to their current
bounds.

The nested `conversations` object maps each character ID to entries with:

| Field | Type | Meaning |
|---|---|---|
| `player` | String | Player input from that exchange. |
| `reply` | String | Character prose returned for that exchange. |

Each `persona_history` entry contains:

| Field | Type | Meaning |
|---|---|---|
| `kind` | String | Either `talk` or `examine`. |
| `input` | String | Player input judged on that turn. |

### `GET /tracks`

Read current character attitude values without retrieving the full save.

**Query parameters**

| Parameter | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |

```http
GET /tracks?session=save-slot-1
```

**Returns — `200 OK`**

```json
{
  "session": "save-slot-1",
  "tracks": {
    "disposition": {"mira": 0.5},
    "fear": {"mira": 0.0}
  }
}
```

`tracks` is keyed by track ID, then character ID. Values are current absolute
values, not changes from the previous turn.

### `GET /persona`

Read current session-wide player persona values.

**Query parameters**

| Parameter | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |

```http
GET /persona?session=save-slot-1
```

**Returns — `200 OK`**

```json
{
  "session": "save-slot-1",
  "persona": {
    "careful_investigator": 0.25
  }
}
```

`persona` is keyed by the dimension IDs declared in `pack.yaml`.

### `GET /journal`

Read the player-facing journal for learned facts.

**Query parameters**

| Parameter | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |

```http
GET /journal?session=save-slot-1
```

**Returns — `200 OK`**

```json
{
  "session": "save-slot-1",
  "journal": [
    {
      "id": "altered_ledger",
      "journal_text": "The final delivery time was overwritten in darker ink."
    }
  ]
}
```

Each journal entry contains:

| Field | Type | Meaning |
|---|---|---|
| `id` | String | Learned fact ID. |
| `journal_text` | String | Exact player-facing text authored for that fact. |

Entries are returned in discovery order. This endpoint exposes only learned
facts; it does not reveal undiscovered fact metadata.

## Response calls

Response calls invoke a character or narrator model using DARPS context.
`/talk` and `/examine` process player input and may produce validated narrative
changes. `/narrate` is a display-only scene-writing call and never changes
state. The host always chooses the operation and any target.

All three calls accept an optional `world` object and return the
[response result object](#response-result-object).

### The `world` object

`world` is a one-call snapshot of host-owned state. It is never saved by
DARPS. Unknown fields produce `400 bad_request`.

| Field | Required? | Type | Meaning | If omitted |
|---|---:|---|---|---|
| `location` | No | String pack location ID | Current location for this interaction. It grounds location knowledge and narration but does not move the player or persist a position. Use the canonical ID. | Uses `start_location` from `pack.yaml`. |
| `accessible_items` | No | Array of string pack item IDs | Items the host has made available in this interaction. It grounds scene-object context and restricts item examination. Use IDs, not names or aliases; send `[]` when none are available. | All pack items remain examination candidates as a permissive development fallback, while the response model is told that the host did not establish a scene-item list. |
| `flags` | No | Object mapping strings to booleans | Current host-owned progress signals used by `when` gates. Per-request values override the same names read from `flags_file`. | Uses `flags_file` values if configured; otherwise an empty object. |

For example:

```json
{
  "location": "workshop",
  "accessible_items": ["ledger"],
  "flags": {
    "workshop_unlocked": true,
    "alarm_disabled": false
  }
}
```

The nested `flags` object uses arbitrary host-defined names:

| Flag value | Type | Meaning |
|---|---|---|
| Key | String | Flag name referenced by pack `when` gates. |
| Value | Boolean | Current state of that host-owned flag. |

### `POST /talk`

Ask one character to respond to the player.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID and narrative memory. |
| `character` | Yes | String character ID | Exact ID of the character being addressed. Names and aliases are not accepted here. |
| `message` | No | String | Player speech or conversational action. Defaults to an empty string; normal integrations should provide it. |
| `world` | No | World object | Ephemeral host-owned context for this turn. |
| `tone` | No | String | Optional host assessment such as `polite`, `probing`, or `hostile`. It overrides tone classification. Guardrail screening still runs when enabled. |

```json
{
  "session": "save-slot-1",
  "character": "mira",
  "message": "When did the clock arrive?",
  "tone": "probing",
  "world": {
    "location": "workshop",
    "accessible_items": ["ledger"],
    "flags": {"workshop_unlocked": true}
  }
}
```

**Returns — `200 OK`**

```json
{
  "speaker": "Mira Vale",
  "prose": "It arrived on Tuesday, shortly before closing.",
  "tone": "probing",
  "deltas": {
    "tracks": {"disposition": {"mira": 0.25}},
    "persona": {"careful_investigator": 0.25},
    "facts_learned": [],
    "canon_added": []
  }
}
```

The result uses the shared [response result object](#response-result-object).
The `speaker` is normally the addressed character's display name.

### `POST /examine`

Ask DARPS to narrate an examination of one host-authorized item or the current
location.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID and narrative memory. |
| `target` | Yes | String | Entity the host authorizes the player to examine. Prefer an accessible item ID or the current location ID. Item/location names and aliases are also resolved. |
| `message` | No | String | What the player does or notices within the target. Together with `target`, this supplies direct-trigger text. The optional examine resolver interprets `message` semantically. An empty value becomes `examine <target>`. |
| `world` | No | World object | Ephemeral host-owned context for this turn. `world.location` is the surrounding location; it is not a top-level request field. |
| `tone` | No | String | Optional host assessment such as `careful` or `hurried`. It overrides tone classification but does not authorize discoveries. |

```json
{
  "session": "save-slot-1",
  "target": "ledger",
  "message": "Compare the overwritten entry with the surrounding ink.",
  "tone": "careful",
  "world": {
    "location": "workshop",
    "accessible_items": ["ledger"],
    "flags": {"workshop_unlocked": true}
  }
}
```

**Returns — `200 OK`**

```json
{
  "speaker": null,
  "prose": "The final time is darker than every entry around it.",
  "tone": "careful",
  "deltas": {
    "tracks": {},
    "persona": {"careful_investigator": 0.5},
    "facts_learned": [
      {
        "id": "altered_ledger",
        "journal_text": "The final delivery time was overwritten in darker ink."
      }
    ],
    "canon_added": []
  }
}
```

The narrator uses `speaker: null`. Facts appear in `facts_learned` only after
their examination source and linked fact gates pass.

#### How `target` is resolved

DARPS resolves and validates `target` before classification, narration, or
state changes:

1. An accessible item's exact ID, name, or alias resolves to that item.
2. The current location's ID, name, or alias resolves to that location.
3. A known item excluded from a supplied `world.accessible_items` list is
   rejected.
4. A known pack location other than `world.location` is rejected.
5. With `strict_items: false` (the default), any remaining noun is treated as
   an unmodelled part of the current location.
6. With `strict_items: true`, that loose-noun fallback is rejected.

For strict integrations, use canonical targets and put subarea detail in
`message`:

```json
{
  "session": "save-slot-1",
  "target": "workshop",
  "message": "Search the drawers beneath the main bench.",
  "world": {
    "location": "workshop",
    "accessible_items": []
  }
}
```

Here `world.location` answers “where is this happening?”, `target` answers
“what may be examined?”, and `message` identifies the relevant detail or
action.

After target resolution, DARPS considers only that entity's
`examine_reveals`. Direct triggers, source `when`, and linked-fact gates remain
engine-enforced. With `examine_resolver: true`, one optional classifier call
may add semantic matches from eligible unmatched trigger groups; it cannot
bypass any gate.

### `POST /narrate`

Ask DARPS to write general scene prose for the host to display. This is useful
for entering a room, weather or ambience, camera transitions, and other
presentation moments that are not player examinations.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID whose learned facts and enabled canon may ground the prose. |
| `instruction` | No | String | Host direction for this one narration, such as `Describe the room as the storm cuts the lights`. Defaults to a brief description of the current scene. This is an instruction, not player input. |
| `world` | No | World object | Ephemeral location, accessible objects, and flags for this scene. |
| `tone` | No | String | Desired presentation tone. Defaults to `neutral`; it is not classified. |

```json
{
  "session": "save-slot-1",
  "instruction": "Describe the workshop as the lights fail.",
  "tone": "ominous",
  "world": {
    "location": "workshop",
    "accessible_items": ["ledger"],
    "flags": {"alarm_disabled": true}
  }
}
```

**Returns — `200 OK`**

```json
{
  "speaker": null,
  "prose": "The lamps gutter out, leaving the workshop to the rain-streaked windows.",
  "tone": "ominous",
  "deltas": {
    "tracks": {},
    "persona": {},
    "facts_learned": [],
    "canon_added": []
  }
}
```

General narration is deliberately read-only. It does not increment the turn,
run input, attitude, persona, knowledge, or examine classifiers, update
conversation history or hint pacing, reveal facts, add canon, or autosave.
If the host event establishes narrative truth, call the relevant
[host mutation](#host-mutations) separately.

### Response result object

`POST /talk`, `POST /examine`, `POST /narrate`, and the final event from their
streaming variants use the same result shape.

| Field | Type | Meaning |
|---|---|---|
| `speaker` | String or null | Character display name for dialogue; `null` for narration or a meta response. |
| `prose` | String | Displayable response with the model's hidden events block removed. |
| `tone` | String | Tone used for the response, supplied by the host or classifier. |
| `deltas` | Deltas object | Validated narrative changes produced by this turn. |

The nested `deltas` object contains:

| Field | Type | Meaning |
|---|---|---|
| `tracks` | Object | Changed absolute track values, keyed by track ID and then character ID. Empty when no track changed. |
| `persona` | Object | Changed absolute persona values keyed by dimension ID. Empty when no dimension changed. |
| `facts_learned` | Array of fact-delta objects | Facts newly learned this turn. Empty for facts already held or blocked by gates. |
| `canon_added` | Array of strings | Canon entries accepted this turn. Empty when none were added or canon building is disabled. |

Each `facts_learned` entry contains:

| Field | Type | Meaning |
|---|---|---|
| `id` | String | Newly learned fact ID. |
| `journal_text` | String | Exact authored journal text associated with that fact. |

## Streaming response calls

Streaming variants accept the same parameters as their blocking counterparts,
but return prose incrementally as Server-Sent Events. Narrative truth is sent
only once, after the complete model response passes validation.

### `POST /talk/stream`

Stream a character response.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |
| `character` | Yes | String character ID | Exact character being addressed. |
| `message` | No | String | Player speech or conversational action. |
| `world` | No | World object | One-call host context, identical to `POST /talk`. |
| `tone` | No | String | Optional host-supplied tone override. |

The fields have the same behavior as [`POST /talk`](#post-talk).

**Returns — `200 OK`, `text/event-stream`**

Zero or more text frames:

```text
data: {"type":"text","text":"It arrived on "}

data: {"type":"text","text":"Tuesday afternoon."}
```

Then exactly one completion frame containing the normal response result:

```text
event: done
data: {"speaker":"Mira Vale","prose":"It arrived on Tuesday afternoon.","tone":"probing","deltas":{"tracks":{},"persona":{},"facts_learned":[],"canon_added":[]}}
```

### `POST /examine/stream`

Stream narrator prose for an examination.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |
| `target` | Yes | String | Host-authorized examination target. |
| `message` | No | String | Examination action or detail. |
| `world` | No | World object | One-call host context, identical to `POST /examine`. |
| `tone` | No | String | Optional host-supplied tone override. |

The fields have the same behavior as [`POST /examine`](#post-examine).

**Returns — `200 OK`, `text/event-stream`**

The endpoint emits the same text-frame sequence and final `done` event as
`POST /talk/stream`. The final event contains the standard response result,
normally with `speaker: null`.

### `POST /narrate/stream`

Stream display-only general narration.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |
| `instruction` | No | String | One-call host direction, identical to `POST /narrate`. |
| `world` | No | World object | One-call host context, identical to `POST /narrate`. |
| `tone` | No | String | Desired presentation tone; defaults to `neutral`. |

**Returns — `200 OK`, `text/event-stream`**

The endpoint emits the same text-frame sequence and final `done` event as the
other streaming calls. The final result always has `speaker: null` and empty
delta collections. The call remains entirely read-only.

Never infer discoveries or state changes from text frames. Only the final
`done` event contains validated truth. If a failure occurs after streaming
headers are sent, the server emits an `event: error` frame; see
[Streaming and errors](../integration/streaming-errors.md).

## Host mutations

Host mutations update DARPS narrative memory without calling a model. Use them
when a cutscene, quest system, gift, rescue, or other host-controlled event
changes what DARPS should remember.

### `POST /adjust_track`

Set or change one character attitude track. Supply exactly one of `change` or
`value`.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |
| `character` | Yes | String character ID | Character whose attitude changes. |
| `track` | No | String track ID | Track to modify. Defaults to the pack's `default_track`. |
| `change` | One of `change`/`value` | Number | Amount to add to the current value. |
| `value` | One of `change`/`value` | Number | New absolute value. |

```json
{
  "session": "save-slot-1",
  "character": "mira",
  "track": "disposition",
  "change": 0.5
}
```

**Returns — `200 OK`**

```json
{
  "deltas": {
    "tracks": {
      "disposition": {"mira": 0.75}
    }
  }
}
```

The returned number is the new absolute value after clamping to the authored
track bounds.

### `POST /grant_fact`

Record that the player learned an authored fact through a host-controlled
event.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |
| `fact` | Yes | String fact ID | Fact to add to the journal. |

```json
{
  "session": "save-slot-1",
  "fact": "altered_ledger"
}
```

**Returns — `200 OK`**

```json
{
  "deltas": {
    "facts_learned": [
      {
        "id": "altered_ledger",
        "journal_text": "The final delivery time was overwritten in darker ink."
      }
    ]
  }
}
```

This endpoint deliberately bypasses the fact's discovery gates because the
host is authoritative over its own story events. Granting an already learned
fact is an idempotent no-op and returns:

```json
{"deltas": {"facts_learned": []}}
```

### `POST /add_canon`

Add host-authored narrative truth established outside a model response.

**JSON body**

| Field | Required? | Type | Meaning |
|---|---:|---|---|
| `session` | Yes | String | Active session ID. |
| `text` | Yes | String | Non-empty canon entry. Whitespace is normalized and the result may contain at most 500 characters. |

```json
{
  "session": "save-slot-1",
  "text": "The workshop alarm was disabled at 9:30 pm."
}
```

**Returns — `200 OK`**

```json
{
  "deltas": {
    "canon_added": [
      "The workshop alarm was disabled at 9:30 pm."
    ]
  }
}
```

Duplicate text is an idempotent no-op. When `canon: false`, host additions are
also ignored. Both cases return:

```json
{"deltas": {"canon_added": []}}
```

## Errors

Errors use one JSON shape across non-streaming endpoints. Hosts should log the
optional diagnostic ID because the DARPS process prints the same ID beside its
traceback.

```json
{
  "error": {
    "code": "invalid_state",
    "message": "state belongs to another pack",
    "diagnostic_id": "optional"
  }
}
```

The nested `error` object contains:

| Field | Type | Meaning |
|---|---|---|
| `code` | String | Stable machine-readable error category. |
| `message` | String | Human-readable explanation suitable for logs. |
| `diagnostic_id` | String, optional | ID matching the server-side traceback for unexpected/provider failures. |

| HTTP status | Typical code | Meaning |
|---:|---|---|
| `400` | `bad_request` or `invalid_state` | Missing field, invalid value, malformed JSON, or incompatible save state. |
| `404` | `unknown_session` or `not_found` | Session or route does not exist. |
| `409` | `session_conflict` | Explicit session ID is already active. |
| `500` | `engine_error` | Unexpected DARPS failure. |
| `502` | `provider_error` | Model provider failed. |

Streaming calls use the same error object inside an SSE `event: error` frame
when failure occurs after headers have been sent. See
[Streaming and errors](../integration/streaming-errors.md) for the wire format.
