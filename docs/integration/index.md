# Host integration

Run DARPS as a localhost sidecar when the host cannot embed Python:

```bash
python -m darps serve packs/my-game --host 127.0.0.1 --port 8080
```

The normal lifecycle is:

1. Wait for `GET /health`.
2. Inspect secret-safe capabilities through `GET /pack` if building a generic
   client.
3. Create or restore a session with `POST /session`.
4. Call `/talk`, `/examine`, or their streaming variants.
5. Mirror useful validated deltas into host systems.
6. Persist `GET /state` in the host save slot.
7. Close unused sessions.

## World ownership

Supply a fresh world snapshot with response calls:

```json
{
  "location": "workshop",
  "present": ["mira"],
  "accessible_items": ["camera", "ledger"],
  "flags": {"workshop_unlocked": true}
}
```

All keys are optional. The snapshot lasts for one call and is never persisted.
If `accessible_items` is provided, it limits which pack items DARPS may
describe or examine. Supply an empty list when no pack items are available.

## Host-authority writes

Host events can update narrative memory without an LLM call:

- `/adjust_track`: a gift, rescue, betrayal, or other game event changes an
  attitude.
- `/grant_fact`: a cutscene teaches an authored fact and resets hint pacing.
- `/add_canon`: a host event establishes incidental narrative truth.

Flags do not need a mutation endpoint: they remain host-owned and are supplied
with subsequent world snapshots.
