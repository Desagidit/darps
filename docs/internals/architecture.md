# Architecture

DARPS is intentionally small: one orchestrator coordinates content loading,
classification, response generation, validation, and state application.

```mermaid
flowchart TB
    Server["server.py\nHTTP sessions"] --> Orchestrator["orchestrator.py\ncall pipeline"]
    CLI["cli.py\ndev harness"] --> Orchestrator
    Orchestrator --> Content["content.py\npack loading + scoped context"]
    Orchestrator --> LLM["llm.py\nproviders + logs"]
    Orchestrator --> Validate["validate.py\nevent gate"]
    Validate --> Conditions["conditions.py\nclosed gate vocabulary"]
    Orchestrator --> State["state.py\nversioned narrative memory"]
    Lint["lint.py\nstatic reachability"] --> Content
    Lint --> Conditions
```

## Module responsibilities

| Module | Owns | Must not own |
|---|---|---|
| `orchestrator.py` | Call pipelines, context selection, pacing, deltas | Pack-specific story logic |
| `content.py` | Pack loading, prompt layering, knowledge rendering | State mutation |
| `conditions.py` | Closed runtime condition evaluation | Arbitrary expressions |
| `validate.py` | Filtering model-proposed events | Unvalidated state writes |
| `state.py` | State shape, normalization, local harness saves | Host world state |
| `llm.py` | Provider adapters, streaming, call logs | Narrative policy |
| `lint.py` | Static schema and reachability checks | Runtime-only semantics that disagree with validation |
| `server.py` | Local transport, sessions, locks, structured errors | Persistence |

## Ownership boundary

```mermaid
flowchart LR
    subgraph Host["Host-owned"]
      World["location, accessible items, flags"]
      Flags["flags and quest progress"]
      Slots["save slots"]
    end
    subgraph Engine["DARPS-owned"]
      Journal["facts + journal"]
      Attitudes["character tracks"]
      Persona["player persona"]
      Canon["canon + conversations"]
    end
    subgraph Pack["Pack-authored"]
      Entities["entities + knowledge"]
      FactWeb["facts + conditions"]
      Guidance["voice + guidance + prose"]
    end
    Host --> Engine
    Pack --> Engine
```

The host sends world state but DARPS never persists it. DARPS returns deltas
but never performs host-game actions.
