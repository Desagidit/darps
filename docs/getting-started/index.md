# Getting started

## Install

DARPS requires Python and PyYAML. Create a virtual environment and install the
runtime dependency:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

On macOS or Linux, activate `.venv/bin/python` instead.

Copy `.env.example` to `.env`, add the key required by your selected provider,
and review `config.yaml`. Ollama and LM Studio can run locally without a key.

## Validate and run the reference pack

```bash
python -m darps validate packs/ashworth-manor
python -m darps play packs/ashworth-manor
```

The development harness stands in for a host game:

```text
@butler What did you hear last night?
x desk search the drawers
/flag cabinet_open
/journal
```

To expose the real integration interface:

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

Next, either [create a pack](first-pack.md) or [connect a host](connect-host.md).
