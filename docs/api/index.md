# API overview

| Endpoint | LLM | Reads state | Changes state | Streams |
|---|---:|---:|---:|---:|
| `GET /health` | No | No | No | No |
| `GET /pack` | No | No | No | No |
| `POST /session` | No | Optional restore | Creates session | No |
| `GET /state` | No | Yes | No | No |
| `POST /state` | No | Yes | Replaces state | No |
| `GET /tracks` | No | Yes | No | No |
| `GET /persona` | No | Yes | No | No |
| `GET /journal` | No | Yes | No | No |
| `POST /talk` | Yes | Yes | Yes | No |
| `POST /talk/stream` | Yes | Yes | At `done` | Yes |
| `POST /examine` | Yes | Yes | Yes | No |
| `POST /examine/stream` | Yes | Yes | At `done` | Yes |
| `POST /adjust_track` | No | Yes | Yes | No |
| `POST /grant_fact` | No | Yes | Yes | No |
| `POST /add_canon` | No | Yes | Yes | No |

All POST bodies are JSON objects. Session-scoped endpoints require `session`.
See the [complete HTTP reference](http-reference.md) and
[streaming/error contract](../integration/streaming-errors.md).
