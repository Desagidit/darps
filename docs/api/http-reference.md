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
| `flags` | Object mapping string names to booleans | Supplies host-owned progress signals used by conditions. | Empty, plus any values read from `flags_file`. |

`present`, `carried`, and `in_reach` are not world fields and are rejected.
Physical presence does not determine what a character remembers; shared
knowledge is retrieved from the addressee's scope-filtered knowledge corpus.

### `POST /examine`

```json
{
  "session":"abc123",
  "target":"delivery book",
  "message":"compare the ink",
  "world":{"location":"workshop","accessible_items":["ledger"]}
}
```

The target may be an item ID, name, alias, trigger, or a location-oriented
noun. Discoveries are pre-authorized by deterministic matching and gates.

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
