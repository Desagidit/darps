"""DARPS condition vocabulary — deliberately CLOSED and declarative.

Every gate in a pack (knowledge inclusion, fact reveals) is expressed in this
small language, which is what keeps packs statically validatable and safe to
download. Adding a condition type here REQUIRES adding it to SPEC.md and
teaching lint.py about it in the same commit. Arbitrary expressions are never
accepted.

Vocabulary (spec 5):
  {var: <name>, is: <value|"self">}       ground-truth variable equals value;
                                          "self" = the character in context
  {fact_learned: <fact_id>}               player has learned this fact
  {flag: <name>}                          host flag is set truthy (flags are
                                          the HOST's progress signal: injected
                                          per call and/or read from flags_file)
  {track_gte: {track: <t>, value: <n>, of: <char_id>?}}
                                          relationship track at/above n;
                                          `of` defaults to character in context
  {not: <condition>}                      negation of exactly one condition —
                                          e.g. "include this lie until the
                                          player has clue_c":
                                          {not: {flag: clue_c}}
"""

KNOWN_KEYS = {"var", "fact_learned", "flag", "track_gte", "not"}


def condition_key(cond: dict) -> str | None:
    """The vocabulary key a condition uses, or None if unrecognized."""
    for k in ("var", "fact_learned", "flag", "track_gte", "not"):
        if k in cond:
            return k
    return None


def is_known(cond) -> bool:
    """Recursively valid vocabulary? Used so `not` can NEVER turn an unknown
    condition into True — negation must not weaken fail-closed."""
    if not isinstance(cond, dict):
        return False
    key = condition_key(cond)
    if key is None:
        return False
    if key == "not":
        return is_known(cond["not"])
    return True


def evaluate(cond: dict, *, vars: dict, state: dict, manifest: dict,
             self_id: str | None = None, track_slack: int = 0,
             tracks_enabled: bool = True) -> bool:
    """Evaluate one condition. Unknown condition types evaluate False
    (fail closed) — lint.py flags them at author time so this should
    never be hit in a validated pack.

    `tracks_enabled=False` (config `tracks: false`) switches the attitude
    mechanic off: track_gte gates evaluate True, because the author's gate is
    about a mechanic the host has disabled — otherwise those reveals would be
    locked forever.
    """
    key = condition_key(cond)
    if key == "var":
        actual = vars.get(cond["var"])
        expected = cond.get("is")
        return actual == self_id if expected == "self" else actual == expected
    if key == "fact_learned":
        return cond["fact_learned"] in state["facts_learned"]
    if key == "flag":
        return bool(state.get("flags", {}).get(cond["flag"]))
    if key == "track_gte":
        if not tracks_enabled:
            return True
        spec = cond["track_gte"]
        track, threshold = spec["track"], spec["value"]
        of = spec.get("of", self_id)
        default = manifest.get("tracks", {}).get(track, {}).get("default", 0)
        current = state.get("tracks", {}).get(track, {}).get(of, default)
        return current >= threshold - track_slack
    if key == "not":
        inner = cond["not"]
        if not is_known(inner):
            return False   # malformed inner: stay fail-closed, never fail open
        return not evaluate(inner, vars=vars, state=state, manifest=manifest,
                            self_id=self_id, track_slack=track_slack,
                            tracks_enabled=tracks_enabled)
    return False


def all_hold(conds: list | None, **kw) -> bool:
    return all(evaluate(c, **kw) for c in (conds or []))
