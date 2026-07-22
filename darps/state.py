"""Narrative session state — the ONLY thing DARPS persists.

DARPS is a conversation layer, not a game coordinator: the host owns the world
(who is where, what is carried, progress flags). What DARPS remembers is the
narrative it is the authority on: which facts the player has learned, how each
character feels, what has been said, and what has become canon.

The versioned, pack-bound blob is the save file. Hosts round-trip it through
GET/POST /state (server) or store it themselves (library).
"""
import json
from pathlib import Path

STATE_VERSION = 1


def pack_id(manifest: dict) -> str:
    """Stable wire/save identifier derived from the required pack name."""
    return "".join(c if c.isalnum() or c in "-_" else "-"
                   for c in manifest["name"].lower()).strip("-")


def new_state(manifest: dict) -> dict:
    return {
        "state_version": STATE_VERSION,
        "pack_id": pack_id(manifest),
        "turn": 0,
        "facts_learned": [],  # ordered fact ids the player has learned
        "tracks": {t: {} for t in manifest.get("tracks", {})},  # track -> char -> value
        "canon": [],         # canon_additions accumulated across the session
        "conversations": {},  # character id -> [{"player":..., "reply":...}]
        "fruitless_turns": 0,  # relevant turns without a new fact (drives hints)
        "persona": {p: spec.get("default", 0)
                    for p, spec in (manifest.get("persona", {}) or {}).items()},
        "persona_history": [],  # recent [{kind,input}] used only for adjudication
    }


def normalize_state(pack, supplied: dict) -> dict:
    """Validate an untrusted save blob and return a complete canonical state.

    Restore is strict about identity and value types, but tolerant of omitted
    narrative fields: missing fields receive current defaults. Unknown ids are
    rejected rather than retained where they could corrupt later prompts.
    """
    if not isinstance(supplied, dict):
        raise ValueError("state must be a JSON object")
    manifest = pack.manifest()
    expected_id = pack_id(manifest)
    if supplied.get("state_version") != STATE_VERSION:
        raise ValueError(f"unsupported state_version {supplied.get('state_version')!r}; "
                         f"expected {STATE_VERSION}")
    if supplied.get("pack_id") != expected_id:
        raise ValueError(f"state belongs to pack {supplied.get('pack_id')!r}; "
                         f"this server is {expected_id!r}")
    state = new_state(manifest)
    facts, characters = pack.facts(), pack.characters()
    fact_ids, character_ids = set(facts), set(characters)

    turn = supplied.get("turn", 0)
    fruitless = supplied.get("fruitless_turns", 0)
    if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
        raise ValueError("state.turn must be a non-negative integer")
    if isinstance(fruitless, bool) or not isinstance(fruitless, int) or fruitless < 0:
        raise ValueError("state.fruitless_turns must be a non-negative integer")
    state["turn"], state["fruitless_turns"] = turn, fruitless

    learned = supplied.get("facts_learned", [])
    if not isinstance(learned, list) or any(fid not in fact_ids for fid in learned):
        raise ValueError("state.facts_learned must contain only known fact ids")
    state["facts_learned"] = list(dict.fromkeys(learned))

    canon = supplied.get("canon", [])
    if not isinstance(canon, list) or any(not isinstance(x, str) for x in canon):
        raise ValueError("state.canon must be a list of strings")
    state["canon"] = list(canon)

    conversations = supplied.get("conversations", {})
    if not isinstance(conversations, dict) or any(cid not in character_ids
                                                  for cid in conversations):
        raise ValueError("state.conversations must use known character ids")
    for cid, history in conversations.items():
        if not isinstance(history, list) or any(
                not isinstance(entry, dict)
                or not isinstance(entry.get("player"), str)
                or not isinstance(entry.get("reply"), str)
                for entry in history):
            raise ValueError(f"state.conversations.{cid} must be player/reply entries")
        state["conversations"][cid] = [
            {"player": entry["player"], "reply": entry["reply"]}
            for entry in history]

    tracks = supplied.get("tracks", {})
    if not isinstance(tracks, dict) or any(t not in manifest.get("tracks", {})
                                           for t in tracks):
        raise ValueError("state.tracks contains an unknown track id")
    for track, per_character in tracks.items():
        if not isinstance(per_character, dict) or any(cid not in character_ids
                                                       for cid in per_character):
            raise ValueError(f"state.tracks.{track} must use known character ids")
        bounds = manifest["tracks"][track]
        for cid, value in per_character.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"state.tracks.{track}.{cid} must be numeric")
            state["tracks"][track][cid] = max(
                bounds.get("min", -3), min(bounds.get("max", 3), float(value)))

    persona_specs = manifest.get("persona", {}) or {}
    persona = supplied.get("persona", {})
    if not isinstance(persona, dict) or any(pid not in persona_specs for pid in persona):
        raise ValueError("state.persona contains an unknown dimension id")
    for pid, value in persona.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"state.persona.{pid} must be numeric")
        spec = persona_specs[pid]
        state["persona"][pid] = max(
            spec.get("min", -3), min(spec.get("max", 3), float(value)))

    persona_history = supplied.get("persona_history", [])
    if not isinstance(persona_history, list) or any(
            not isinstance(entry, dict)
            or entry.get("kind") not in ("talk", "examine")
            or not isinstance(entry.get("input"), str)
            for entry in persona_history):
        raise ValueError("state.persona_history must contain talk/examine input entries")
    state["persona_history"] = [
        {"kind": entry["kind"], "input": entry["input"]}
        for entry in persona_history]
    return state


def save_path(pack_name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in pack_name.lower())
    return Path.cwd() / "saves" / f"{safe}.json"


def save(state: dict, pack_name: str) -> None:
    p = save_path(pack_name)
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def load_or_new(pack) -> dict:
    manifest = pack.manifest()
    p = save_path(manifest["name"])
    if p.exists():
        return normalize_state(pack, json.loads(p.read_text(encoding="utf-8")))
    return new_state(manifest)
