# Connect a host game

Create a live session:

```bash
curl -X POST http://127.0.0.1:8080/session \
  -H "Content-Type: application/json" \
  -d '{}'
```

Talk to a character. The host—not DARPS—chooses the addressee:

```json
{
  "session": "SESSION_ID",
  "character": "butler",
  "message": "What did you hear last night?",
  "world": {
    "location": "study",
    "present": ["butler"],
    "accessible_items": ["notebook", "brandy_glass"],
    "flags": {"cabinet_open": false}
  }
}
```

Send it to `POST /talk`. A result contains display prose and validated changes:

Every key in `world` is optional and lasts for one call. A production host
normally supplies `accessible_items` as the authoritative list of pack items
available in that interaction—even when the list is empty. When present, it
limits examination and tells DARPS which item context may enter the prompt.
DARPS never persists or changes this list.

```json
{
  "speaker": "Mr. Halloway",
  "prose": "I heard nothing that concerns the police.",
  "tone": "probing",
  "deltas": {
    "tracks": {"disposition": {"butler": -0.5}},
    "persona": {},
    "facts_learned": [],
    "canon_added": []
  }
}
```

Persist the complete object returned by `GET /state?session=...`. Your main
save file must separately preserve host-owned location, inventory, quests, and
flags. See [state and save games](../concepts/state-saves.md).
