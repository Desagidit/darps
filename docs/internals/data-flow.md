# Information and data flow

## Talk

```mermaid
sequenceDiagram
    participant H as Host
    participant D as DARPS
    participant C as Classifier model
    participant R as Character model
    participant V as Validator

    H->>D: talk(character, message, world)
    D->>D: merge narrative state + world snapshot
    D->>C: screen input (when required)
    C-->>D: tone, topics, rails, mentions
    D->>C: persona criteria + player input
    C-->>D: persona shifts
    D->>C: attitude guidance + player input
    C-->>D: track shifts
    D->>D: assemble scoped briefing and reveal authority
    D->>R: character prompt
    R-->>D: prose + proposed events
    D->>V: proposals + authority + gates
    V-->>D: approved events
    D->>D: apply narrative state and deltas
    D-->>H: prose + validated deltas
```

## Examine

```mermaid
sequenceDiagram
    participant H as Host
    participant D as DARPS
    participant N as Narrator model
    participant V as Validator

    H->>D: examine(target, message, world)
    D->>D: resolve reachable item / current location
    D->>D: match triggers and evaluate gates
    D->>D: build authorized discovery set
    D->>N: narrator prompt + authorization
    N-->>D: prose + proposed events
    D->>V: proposals + authorized set
    V-->>D: approved reveals
    D-->>H: narration + validated deltas
```

## Character context assembly

```mermaid
flowchart TD
    World["world.md"] --> Briefing
    Character["voice + background"] --> Briefing
    Own["condition-passing own knowledge"] --> Briefing
    Relevant["relevant, scoped shared knowledge"] --> Briefing
    Canon["enabled canon"] --> Briefing
    Journal["learned facts"] --> Briefing
    History["character conversation history"] --> Briefing
    Track["selected track prose—not numbers"] --> Briefing
    Scene["host-declared scene"] --> Briefing
    Briefing["Scoped character prompt"] --> Model
```

Ground-truth variables never enter prompts directly. They only decide whether
gated content exists in the assembled context.

## Streaming truth boundary

```mermaid
flowchart LR
    Model --> Detector["incremental fence detector"]
    Detector -->|"prose chunks"| Host
    Detector -->|"buffer events"| Complete["complete response"]
    Complete --> Validator
    Validator --> State
    State -->|"done + result"| Host
```
