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
  "world":{"location":"workshop","present":["mira"],"accessible_items":["ledger"]},
  "tone":"probing"
}
```

`tone` is optional. The character ID must exist; DARPS never guesses the
addressee.

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
