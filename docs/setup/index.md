# Quick Start

## Install

DARPS sits as a layer between your game and the LLM. It requires Python and PyYAML. Create a virtual environment and install the runtime dependency:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

On macOS or Linux, activate `.venv/bin/python` instead.

Copy `.env.example` to `.env`, add the key required by your selected provider, and review `config.yaml`. Ollama and LM Studio can run locally without a key.

## Validate and run the reference pack

DARPS comes with a minimal pack for the sake of example. Ashworth Manor is a tiny murder mystery.

```bash
python -m darps validate packs/ashworth-manor
python -m darps play packs/ashworth-manor
```

The development harness can be used as a stand in for a host game:

```text
@butler What did you hear last night?
x desk search the drawers
/flag cabinet_open
/journal
```

Expose the real integration interface:

```bash
python -m darps serve packs/ashworth-manor
```

The sidecar listens on `http://127.0.0.1:8080` by default.

## Confirm the server

```bash
curl http://127.0.0.1:8080/health
```

```json
{"status":"ok","pack":"Ashworth Manor"}
```

## Next steps

To make your own game work with DARPS you'll have to:

- Learn about [DARPS concepts](../concepts/index.md).
- [Create a pack](first-pack.md) a pack that defines your world, its items, locations, characters and logic.
- [Connect your game to DARPS](connect-host.md).
