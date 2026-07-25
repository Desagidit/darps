# HTTP API reference

## Health and metadata

### `GET /health`

Returns server readiness and the loaded pack display name.

### `GET /pack`

Returns secret-safe integration metadata: pack identity/spec, entity IDs,
display names and aliases, numeric track/persona definitions, default track,
and capabilities. It excludes facts, descriptions, variables, knowledge,
conditions, summaries, and prompt guidance.

## Sessions and state

### `POST /session`

Create an empty session with `{}` or restore a state:

```json
{"session":"optional-explicit-id","state":{"state_version":1,"...":"..."}}
```

Returns `{session, state}`. Explicit ID collisions return 409.

### `POST /session/close`

```json
{"session":"abc123"}
```

Closes the in-memory session. It does not delete host save files.

### `GET /state?session=abc123`

Returns the complete versioned state blob for persistence.

### `POST /state`

```json
{"session":"abc123","state":{...}}
```

Validates, normalizes, and replaces an active session's state.

### Focused views

```http
GET /tracks?session=abc123
GET /persona?session=abc123
GET /journal?session=abc123
```

These are UI-friendly views, not independent storage. `/journal` returns
ordered `{id, journal_text}` objects for learned facts only.

## Response calls

### `POST /talk`

```json
{
  "session":"abc123",
  "character":"mira",
  "message":"When did the clock arrive?",
  "world":{"location":"workshop","accessible_items":["ledger"]},
  "tone":"probing"
}
```

| Field | Essential? | Expected type | Purpose |
|---|---:|---|---|
| `session` | Yes | String | Selects the live DARPS session and its narrative state. |
| `character` | Yes | String | Exact pack ID of the character being addressed. |
| `message` | Practically yes | String | The player’s speech or conversational action. Defaults to an empty string. |
| `tone` | No | String | The player's tone. Suitable values are short descriptive labels such as `polite`, `friendly`, `probing`, or `hostile`; there is no fixed enumeration. A host value overrides tone classification. Guardrail screening still runs when enabled. With guardrails disabled, supplying tone skips the general screening call. |
| `world` | No | Object | Ephemeral snapshot of relevant host-owned world state. |

**The world object**

DARPS accepts exactly three world fields. Every field is optional and lasts for
one call only. Unknown fields produce `400 bad_request`.

| Field | Expected type | Purpose | Fallback |
|---|---|---|---|
| `location` | String location ID from the pack | Grounds immediate location knowledge and narration. | Uses `start_location` from `pack.yaml`. |
| `accessible_items` | Array of string item IDs | Authoritative list of pack items available in this interaction; grounds item context and restricts examination. | Omission leaves the development path permissive; production hosts should supply a list, including `[]`. |
| `flags` | Object mapping string names to booleans | Supplies host-owned progress signals used by `when` gates. | Empty, plus any values read from `flags_file`. |

Flags are entirely owned by the game and not by DARPS. However, knowledge can be gated behind flags so this is a good way to optionally inject game state into knowledge checks.

### `POST /examine`

Ask DARPS to narrate an examination of one host-authorized item or the current
location. The host chooses the target; DARPS does not infer what the player can
reach or where the player is.

```json
{
  "session":"abc123",
  "target":"ledger",
  "message":"Compare the overwritten entry with the surrounding ink.",
  "tone":"careful",
  "world":{
    "location":"workshop",
    "accessible_items":["ledger"],
    "flags":{"workshop_unlocked":true}
  }
}
```

#### Request fields

| Field | Essential? | Expected type | How to use it |
|---|---:|---|---|
| `session` | Yes | String | The live DARPS session ID returned by `POST /session`. This selects narrative memory such as learned facts and persona state. |
| `target` | Yes | String | The entity the host is authorizing the player to examine. Prefer an accessible item ID or the current location ID. Item/location names and aliases are also resolved. This is targeting data, not the player's prose. |
| `message` | No | String | What the player does or pays attention to within the target. Together with `target`, it supplies exact-trigger text; it is also the request interpreted by the optional semantic resolver. If omitted or empty, DARPS uses `examine <target>`. |
| `tone` | No | String | Optional host assessment such as `careful`, `hurried`, or `hostile`. It overrides tone classification but does not choose the target or authorize a discovery. |
| `world` | No | Object | A one-call snapshot of host-owned location, item accessibility, and flags. It is never persisted by DARPS. |

There is no separate top-level `location` field. The current location belongs
inside `world`.

#### How `target` is resolved

DARPS resolves and validates `target` before classification, narration, or
state changes:

1. An exact ID or alias/name match against an accessible pack item resolves to
   that item.
2. The current location's ID, name, or alias resolves to the current location.
3. A known item omitted from the supplied `accessible_items` list is rejected.
4. A known pack location other than `world.location` is rejected.
5. With the default `strict_items: false`, any remaining noun is treated as an
   unmodelled part of the current location, such as `desk` or `fireplace`.
6. With `strict_items: true`, that loose-noun fallback is rejected.

For a strict integration, use canonical IDs and put location-subarea detail in
`message`:

```json
{
  "session":"abc123",
  "target":"workshop",
  "message":"Search the drawers beneath the main bench.",
  "world":{
    "location":"workshop",
    "accessible_items":[]
  }
}
```

Here `target` establishes that the examination concerns the current
`workshop` entity. “Drawers beneath the main bench” supplies the detail that
its `examine_reveals[].triggers` may match.

#### The `world` object for examination

`world` accepts exactly the following three fields. Unknown fields produce
`400 bad_request`. Every value applies to this request only.

| `world` field | Essential? | Expected type | How DARPS uses it | If omitted |
|---|---:|---|---|---|
| `location` | No | String pack location ID | Selects the current location description, scenery, examination rules, and location-grounded context. It does not move the player or update a stored position. Use the canonical ID, not a name or alias. | Uses `start_location` from `pack.yaml`. |
| `accessible_items` | No | Array of string pack item IDs | Authoritative item set for this interaction. It limits item target resolution and tells the narrator which pack items the host has established in the scene. Use IDs, not item names or aliases; send `[]` when no pack items are accessible. | All pack items remain target candidates as a permissive development fallback, while the narrator is told that the host did not establish a scene-item list. Production hosts should normally supply this field. |
| `flags` | No | Object mapping string names to booleans | Supplies current host-owned progress state to `when` gates on examination sources and facts. Request flags override identically named values from `flags_file`. DARPS reads but never modifies or persists them. | Uses values from `flags_file`, if configured; otherwise an empty flag map. |

`world.location` answers “where is this interaction happening?”
`target` answers “what has the host allowed the player to examine?” They may
be the same when examining a room generally, but an item target still requires
the surrounding current location:

```json
{
  "session":"abc123",
  "target":"brandy_glass",
  "message":"Sniff what remains at the bottom.",
  "world":{
    "location":"study",
    "accessible_items":["brandy_glass"]
  }
}
```

After resolving the target, DARPS authorizes discoveries only from that
entity's `examine_reveals`. Direct triggers, source `when`, and linked-fact
gates are engine-enforced. With `examine_resolver: true`, DARPS may make one
additional classifier call to add semantic matches from eligible unmatched
trigger groups; returned indexes are validated and cannot bypass any gate.

### Streaming variants

`POST /talk/stream` and `POST /examine/stream` accept the same respective
bodies and use the SSE contract described under
[streaming and errors](../integration/streaming-errors.md).

## Host mutations

### `POST /adjust_track`

Supply exactly one of `change` or `value`:

```json
{"session":"abc123","character":"mira","track":"disposition","change":0.5}
```

The track defaults to the manifest's `default_track` and clamps to bounds.

### `POST /grant_fact`

```json
{"session":"abc123","fact":"altered_ledger"}
```

Bypasses discovery gates because the host is authoritative over its own
cutscenes and systems. Unknown IDs fail; already-held facts are a no-op.

### `POST /add_canon`

```json
{"session":"abc123","text":"The workshop alarm was disabled at 9:30 pm."}
```

Text is required, whitespace-normalized, limited to 500 characters, and
idempotent. With `canon: false`, it is a no-op.

## Result shape

```json
{
  "speaker":"Mira Vale",
  "prose":"...",
  "tone":"probing",
  "deltas":{
    "tracks":{"disposition":{"mira":0.5}},
    "persona":{"careful_investigator":0.25},
    "facts_learned":[{"id":"altered_ledger","journal_text":"..."}],
    "canon_added":[]
  }
}
```
