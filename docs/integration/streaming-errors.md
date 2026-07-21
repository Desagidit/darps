# Streaming and errors

`/talk/stream` and `/examine/stream` use Server-Sent Events over a POST
response. Text frames arrive first:

```text
data: {"type":"text","text":"A bitter almond scent"}

data: {"type":"text","text":" catches in the throat."}
```

Validated truth arrives exactly once:

```text
event: done
data: {"speaker":null,"prose":"...","tone":"neutral","deltas":{...}}
```

Never infer discoveries or other state from streamed prose. The model's events
block remains buffered and hidden until the complete response passes
validation.

If failure occurs after headers were sent:

```text
event: error
data: {"error":{"code":"provider_error","message":"...","diagnostic_id":"..."}}
```

## HTTP errors

All non-streaming errors use:

```json
{"error":{"code":"invalid_state","message":"...","diagnostic_id":"optional"}}
```

| Status | Meaning |
|---:|---|
| 400 | Malformed request, invalid value, or incompatible state |
| 404 | Unknown route or session |
| 409 | Explicit session ID already exists |
| 500 | Unexpected engine failure |
| 502 | Model provider failed or returned an invalid response |

Record `diagnostic_id` in the host's error report. The sidecar prints the same
ID with the traceback.
