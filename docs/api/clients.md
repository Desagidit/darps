# Python and C# clients

## Python library

Python hosts can bypass HTTP:

```python
from darps.content import Pack
from darps.orchestrator import Game
from darps.state import new_state

pack = Pack("packs/my-game")
game = Game(config, pack, new_state(pack.manifest()))

result = game.talk(
    "mira",
    "When did the clock arrive?",
    world={"location": "workshop", "accessible_items": ["ledger"]},
)
print(result["prose"])
```

Library methods mirror the HTTP surface:

- `talk`, `talk_stream`, `examine`, `examine_stream`;
- `adjust_track`, `grant_fact`, `add_canon`;
- direct access to the versioned `game.state` blob.

## C# / Unity

`clients/DarpsClient.cs` documents and implements the wire contract. Typical
usage:

```csharp
using var darps = new DarpsClient("http://127.0.0.1:8080");
if (!await darps.WaitHealthy()) throw new Exception("DARPS did not start");

var session = await darps.NewSession();
var world = new {
    location = "workshop",
    accessible_items = new[] { "ledger" },
    flags = new { workshop_unlocked = true }
};
var result = await darps.Talk(session, "mira", "When did it arrive?", world);
```

The reference client includes streaming, save-state access, pack metadata,
tracks, persona, journal, and all host mutations. Bundle the sidecar or a
frozen executable with the game; do not expose an unauthenticated DARPS server
to an external network.
