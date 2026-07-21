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
  "carried": ["camera"],
  "in_reach": ["ledger"],
  "flags": {"workshop_unlocked": true}
}
```

All keys are optional. The snapshot lasts for one call and is never persisted.
If `carried` or `in_reach` is provided, it also limits which pack items DARPS
may describe as examinable.

## Host-authority writes

Host events can update narrative memory without an LLM call:

- `/adjust_track`: a gift, rescue, betrayal, or other game event changes an
  attitude.
- `/grant_fact`: a cutscene teaches an authored fact and resets hint pacing.
- `/add_canon`: a host event establishes incidental narrative truth.

Flags do not need a mutation endpoint: they remain host-owned and are supplied
with subsequent world snapshots.
