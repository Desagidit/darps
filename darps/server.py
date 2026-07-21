"""darps serve — a localhost HTTP wrapper around the conversation API.

Stdlib only (`http.server`), so a game engine that cannot embed CPython (Unity,
Unreal, Godot, a browser) drives DARPS as a sidecar process over JSON. The host
supplies who is addressed and a small world snapshot per call; DARPS returns
prose + narrative deltas.

Sessions are in-memory and serialized by a per-session lock. Persistence is the
HOST's job via GET/POST `/state` — the server does NOT autosave.

Routes (verb responses are the result dict; see SPEC):
  GET  /health                      -> {"status","pack"}
  GET  /pack                        -> safe integration metadata (no secrets)
  POST /session   {state?,session?} -> {"session","state"}   (new or restored)
  GET  /state?session=ID            -> {"session","state"}
  GET  /tracks?session=ID           -> {"session","tracks"}
  GET  /journal?session=ID          -> learned journal entries
  POST /state     {session,state}   -> {"session","state"}   (restore a save)
  POST /session/close {session}     -> {"closed"}
  POST /talk      {session,character,message,world?,tone?}
  POST /talk/stream  same body -> Server-Sent Events: prose chunks as
                     `data: {"type":"text","text":...}`, then a final
                     `event: done` frame carrying the result dict
  POST /examine   {session,target,message?,world?,tone?}
  POST /examine/stream same body -> Server-Sent Events
  POST /adjust_track {session,character,change?|value?,track?} (no LLM)
  POST /grant_fact {session,fact}                    host-granted fact (no LLM)
  POST /add_canon {session,text}                     host-authored canon (no LLM)
"""
import json
import sys
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import llm, state as state_mod
from .orchestrator import Game


class SessionConflict(ValueError):
    pass


class Registry:
    """Owns the pack + config and the live sessions (id -> [Game, Lock])."""

    def __init__(self, cfg: dict, pack):
        self.cfg = cfg
        self.pack = pack
        self.manifest = pack.manifest()
        self._sessions: dict[str, list] = {}
        self._guard = threading.Lock()

    def create(self, save: dict | None = None, session_id: str | None = None) -> str:
        sid = session_id or uuid.uuid4().hex[:12]
        with self._guard:
            if sid in self._sessions:
                raise SessionConflict(f"session {sid!r} already exists")
            state = (state_mod.normalize_state(self.pack, save) if save is not None
                     else state_mod.new_state(self.manifest))
            self._sessions[sid] = [Game(self.cfg, self.pack, state), threading.Lock()]
        return sid

    def get(self, sid):
        with self._guard:
            return self._sessions.get(sid)

    def close(self, sid) -> None:
        with self._guard:
            self._sessions.pop(sid, None)


# --- verb adapters: JSON body -> Game call. KeyError => a required field is missing.
def _talk(g, d):
    return g.talk(d["character"], d.get("message", ""), world=d.get("world"),
                  tone=d.get("tone"))


def _examine(g, d):
    return g.examine(d["target"], d.get("message", ""), world=d.get("world"),
                     tone=d.get("tone"))


def _adjust_track(g, d):
    return g.adjust_track(d["character"], change=d.get("change"),
                          value=d.get("value"), track=d.get("track"))


def _grant_fact(g, d):
    return g.grant_fact(d["fact"])


def _add_canon(g, d):
    return g.add_canon(d["text"])


_VERBS = {"talk": _talk, "examine": _examine,
          "adjust_track": _adjust_track, "grant_fact": _grant_fact,
          "add_canon": _add_canon}


def _public_entity(entity: dict) -> dict:
    return {key: entity[key] for key in ("id", "name", "aliases")
            if key in entity}


def _pack_metadata(pack) -> dict:
    manifest = pack.manifest()
    numeric = lambda spec: {key: spec[key]
                            for key in ("min", "max", "default", "speed")
                            if key in spec}
    return {
        "pack_id": state_mod.pack_id(manifest),
        "name": manifest["name"],
        "darps_spec": manifest["darps_spec"],
        "characters": [_public_entity(c) for c in pack.characters().values()],
        "locations": [_public_entity(pack.location(lid)) for lid in pack.location_ids()],
        "items": [_public_entity(item) for item in pack.items().values()],
        "tracks": {tid: numeric(spec)
                   for tid, spec in (manifest.get("tracks", {}) or {}).items()},
        "default_track": manifest.get("default_track"),
        "persona": {pid: numeric(spec)
                    for pid, spec in (manifest.get("persona", {}) or {}).items()},
        "capabilities": ["talk", "talk_stream", "examine", "examine_stream",
                         "tracks", "persona", "journal", "canon"],
    }


class _Handler(BaseHTTPRequestHandler):
    registry: Registry = None   # set on the concrete subclass before serving

    # -------------------------------------------------------------- plumbing
    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, code: str, message: str,
                    *, diagnostic_id: str | None = None) -> None:
        error = {"code": code, "message": message}
        if diagnostic_id:
            error["diagnostic_id"] = diagnostic_id
        return self._send(status, {"error": error})

    @staticmethod
    def _diagnostic(exc: Exception) -> str:
        diagnostic_id = uuid.uuid4().hex[:12]
        print(f"DARPS error [{diagnostic_id}]: {exc}", file=sys.stderr)
        traceback.print_exc()
        return diagnostic_id

    def _read_body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        data = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def log_message(self, *args):   # keep stdout clean; calls are logged in llm.py
        pass

    # ------------------------------------------------------------------- GET
    def do_GET(self):
        url = urlparse(self.path)
        reg = self.registry
        if url.path == "/health":
            return self._send(200, {"status": "ok", "pack": reg.manifest.get("name")})
        if url.path == "/pack":
            return self._send(200, _pack_metadata(reg.pack))
        if url.path in ("/state", "/tracks", "/journal", "/persona"):
            sid = (parse_qs(url.query).get("session") or [None])[0]
            entry = reg.get(sid)
            if entry is None:
                return self._send_error(404, "unknown_session",
                                        f"unknown session {sid!r}")
            game, lock = entry
            with lock:
                if url.path == "/state":
                    payload = {"state": game.state}
                elif url.path == "/tracks":
                    payload = {"tracks": game.state.get("tracks", {})}
                elif url.path == "/persona":
                    payload = {"persona": game.state.get("persona", {})}
                else:
                    facts = game.pack.facts()
                    payload = {"journal": [
                        {"id": fid, "journal_text": facts[fid]["journal_text"].strip()}
                        for fid in game.state.get("facts_learned", []) if fid in facts]}
                return self._send(200, {"session": sid, **payload})
        return self._send_error(404, "not_found", f"no route GET {url.path}")

    # ------------------------------------------------------------------ POST
    def do_POST(self):
        url = urlparse(self.path)
        reg = self.registry
        try:
            data = self._read_body()
        except (ValueError, UnicodeDecodeError) as e:
            return self._send_error(400, "bad_request", f"bad JSON body: {e}")

        if url.path == "/session":
            try:
                sid = reg.create(save=data["state"] if "state" in data else None,
                                 session_id=data.get("session"))
            except SessionConflict as e:
                return self._send_error(409, "session_conflict", str(e))
            except ValueError as e:
                return self._send_error(400, "invalid_state", str(e))
            game, lock = reg.get(sid)
            with lock:
                return self._send(200, {"session": sid, "state": game.state})
        if url.path == "/session/close":
            reg.close(data.get("session"))
            return self._send(200, {"closed": data.get("session")})

        entry = reg.get(data.get("session"))
        if entry is None:
            return self._send_error(404, "unknown_session",
                                    f"unknown session {data.get('session')!r}")
        game, lock = entry

        if url.path == "/state":
            with lock:
                if "state" not in data:
                    return self._send_error(400, "bad_request",
                                            "missing required field 'state'")
                try:
                    game.state = state_mod.normalize_state(game.pack, data["state"])
                    game._ensure_track_starts()
                    game._ensure_persona_defaults()
                except ValueError as e:
                    return self._send_error(400, "invalid_state", str(e))
                return self._send(200, {"session": data.get("session"), "state": game.state})

        if url.path in ("/talk/stream", "/examine/stream"):
            # Validate before any bytes go out: once streaming starts, the
            # only failure mode left is closing the connection.
            required = "character" if url.path == "/talk/stream" else "target"
            if required not in data:
                return self._send_error(400, "bad_request",
                                        f"missing required field '{required}'")
            if url.path == "/talk/stream" and data["character"] not in game.pack.characters():
                return self._send_error(400, "bad_request",
                                        f"unknown character id {data['character']!r}")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                with lock:
                    stream = (game.talk_stream(data["character"], data.get("message", ""),
                                               world=data.get("world"), tone=data.get("tone"))
                              if url.path == "/talk/stream" else
                              game.examine_stream(data["target"], data.get("message", ""),
                                                  world=data.get("world"),
                                                  tone=data.get("tone")))
                    for ev in stream:
                        if ev["type"] == "done":
                            self.wfile.write(b"event: done\n")
                            payload = ev["result"]
                        else:
                            payload = ev
                        self.wfile.write(b"data: " + json.dumps(
                            payload, ensure_ascii=False).encode("utf-8") + b"\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionError):
                pass
            except Exception as e:
                if isinstance(e, ValueError):
                    error = {"code": "bad_request", "message": str(e)}
                else:
                    diagnostic_id = self._diagnostic(e)
                    error = {"code": "provider_error" if isinstance(e, llm.ProviderError)
                             else "engine_error", "message": str(e),
                             "diagnostic_id": diagnostic_id}
                try:
                    self.wfile.write(b"event: error\n")
                    self.wfile.write(b"data: " + json.dumps(
                        {"error": error}, ensure_ascii=False).encode("utf-8") + b"\n\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionError):
                    pass
            return

        handler = _VERBS.get(url.path.lstrip("/"))
        if handler is None:
            return self._send_error(404, "not_found", f"no route POST {url.path}")
        try:
            with lock:
                result = handler(game, data)
        except KeyError as e:
            return self._send_error(400, "bad_request", f"missing required field {e}")
        except (ValueError, TypeError) as e:
            return self._send_error(400, "bad_request", str(e))
        except llm.ProviderError as e:
            diagnostic_id = self._diagnostic(e)
            return self._send_error(502, "provider_error", str(e),
                                    diagnostic_id=diagnostic_id)
        except Exception as e:
            diagnostic_id = self._diagnostic(e)
            return self._send_error(500, "engine_error", "internal engine error",
                                    diagnostic_id=diagnostic_id)
        return self._send(200, result)


def make_server(cfg: dict, pack, host: str = "127.0.0.1", port: int = 8080):
    """Build (but don't start) the server. `port=0` binds an ephemeral port —
    read it back from `server.server_address[1]` (used by the test suite)."""
    cfg = {**cfg, "autosave": False}   # host owns persistence via /state
    handler = type("Handler", (_Handler,), {"registry": Registry(cfg, pack)})
    return ThreadingHTTPServer((host, port), handler)


def serve(cfg: dict, pack, host: str = "127.0.0.1", port: int = 8080) -> None:
    httpd = make_server(cfg, pack, host, port)
    bound = httpd.server_address[1]
    print(f"DARPS serving '{pack.manifest().get('name')}' on "
          f"http://{host}:{bound}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping.")
    finally:
        httpd.server_close()
