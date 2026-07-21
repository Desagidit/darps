"""The runtime gate. The LLM proposes events; the engine disposes.

Nothing enters the journal or narrative state unless it passes these checks. A
model that hallucinates a reveal simply has it stripped — the prose may gesture
at something, but no fact is recorded, and the discrepancy is visible in the
logs.
"""
from . import conditions


def filter_track_shifts(events: dict, allowed_tracks: set[str]) -> dict[str, int]:
    """Validate a multi-attitude assessment proposal. Unknown tracks vanish;
    malformed or omitted values become zero."""
    proposed = events.get("shifts")
    if not isinstance(proposed, dict):
        proposed = {}
    out = {}
    for track in allowed_tracks:
        try:
            out[track] = max(-2, min(2, int(proposed.get(track, 0))))
        except (TypeError, ValueError):
            out[track] = 0
    return out


def filter_persona_shifts(events: dict, allowed: set[str]) -> dict[str, int]:
    """Validate session-level persona judgments; unknown dimensions vanish."""
    proposed = events.get("shifts")
    if not isinstance(proposed, dict):
        proposed = {}
    out = {}
    for dimension in allowed:
        try:
            out[dimension] = max(-2, min(2, int(proposed.get(dimension, 0))))
        except (TypeError, ValueError):
            out[dimension] = 0
    return out


def fact_reveal_allowed(fact: dict, *, state: dict, game_vars: dict, manifest: dict,
                        via_character: str | None = None, track_slack: int = 0,
                        tracks_enabled: bool = True) -> bool:
    """Central gating: prerequisites + conditions. Testimony SOURCE authority
    is the caller's job (membership in the character's revealable set — what
    their assembled briefing actually reveals); `via_character` here only
    supplies `self` for condition evaluation."""
    if fact["id"] in state["facts_learned"]:
        return False
    for req in fact.get("requires", []):
        if req not in state["facts_learned"]:
            return False
    return conditions.all_hold(
        fact.get("conditions"), vars=game_vars, state=state, manifest=manifest,
        self_id=via_character, track_slack=track_slack,
        tracks_enabled=tracks_enabled,
    )


def filter_character_events(events: dict, char_id: str, facts: dict, *, state: dict,
                            game_vars: dict, manifest: dict, revealable: set,
                            track_slack: int = 0,
                            tracks_enabled: bool = True,
                            canon_enabled: bool = True) -> dict:
    """Sanitize a character call's events block. `revealable` is the set of
    fact ids the character's effective knowledge carries a `reveals:` policy
    for — reveal authority derives from the briefing itself, so a character
    can never disclose testimony that isn't in their context. `track_slack`
    (hint system) relaxes track_gte thresholds when the forthcoming style is
    active."""
    approved = []
    for fid in events.get("reveals", []) or []:
        fact = facts.get(fid)
        if fact and fid in revealable \
                and fact_reveal_allowed(fact, state=state, game_vars=game_vars,
                                        manifest=manifest, via_character=char_id,
                                        track_slack=track_slack,
                                        tracks_enabled=tracks_enabled):
            approved.append(fid)

    canon_additions = [] if not canon_enabled else [
        f for f in (events.get("canon_additions") or [])
        if isinstance(f, str) and f.strip()
    ][:3]
    return {"reveals": approved, "canon_additions": canon_additions,
            "story_relevance": _clamp_relevance(events)}


def filter_narrator_events(events: dict, authorized: list[str]) -> dict:
    """Narrator may only reveal what the engine pre-authorized this turn."""
    reveals = [f for f in (events.get("reveals") or []) if f in authorized]
    return {"reveals": reveals, "story_relevance": _clamp_relevance(events)}


def _clamp_relevance(events: dict) -> int:
    """0-2; defaults to 1 (relevant) so models that omit the field still pace."""
    try:
        return max(0, min(2, int(events.get("story_relevance", 1))))
    except (TypeError, ValueError):
        return 1
