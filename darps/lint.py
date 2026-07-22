"""darps validate — static pack linting.

The promise: if a pack validates, it works. Because gates are declarative
(conditions.py's closed vocabulary), we can check that every fact is reachable
before anyone spends a token on it.

Checks are grouped as ERRORs (pack will misbehave) and WARNINGs (probably a
mistake). Every rule the runtime enforces has a lint twin here — when the
condition vocabulary grows, this file grows in the same commit.
"""
from . import conditions
from .content import Pack

# spec-1 fields the engine no longer reads; warn so migrations aren't silent
_REMOVED_MANIFEST = ("intents", "speech_intents", "discovery_intents",
                     "item_actions", "goals", "hints", "history_turns")
_REMOVED_ITEM = ("portable", "fixed_reason", "start", "interactions")


def lint(pack: Pack) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    m = pack.manifest()
    game_vars = pack.vars()
    facts = pack.facts()
    chars = pack.characters()
    loc_ids = pack.location_ids()
    items = pack.items()
    player = pack.player()

    # ---------------------------------------------------------- manifest
    for field in ("name", "start_location"):
        if field not in m:
            errors.append(f"pack.yaml: missing required field '{field}'")
    if m.get("start_location") and m["start_location"] not in loc_ids:
        errors.append(f"pack.yaml: start_location '{m['start_location']}' has no "
                      f"locations/<id>.yaml file")
    for old in _REMOVED_MANIFEST:
        if old in m:
            warnings.append(f"pack.yaml: '{old}' was removed in spec 2 and is "
                            f"ignored (hints/history are config; intents, goals "
                            f"and item actions are the host game's job)")
    tracks = m.get("tracks", {})
    if "primary_track" in m:
        errors.append("pack.yaml: 'primary_track' was renamed in spec 6; "
                      "use 'default_track'")
    default_track = m.get("default_track")
    if default_track and default_track not in tracks:
        errors.append(f"pack.yaml: default_track '{default_track}' not defined in tracks")
    for track, spec in tracks.items():
        if not isinstance(spec, dict):
            errors.append(f"pack.yaml: track '{track}' must be a mapping")
            continue
        guidance = spec.get("guidance")
        if guidance is not None and (not isinstance(guidance, str) or not guidance.strip()):
            errors.append(f"pack.yaml: track '{track}' guidance must be non-empty text")
    persona = m.get("persona", {}) or {}
    if not isinstance(persona, dict):
        errors.append("pack.yaml: 'persona' must be a mapping of dimensions")
        persona = {}
    for pid, spec in persona.items():
        if not isinstance(pid, str) or not pid.strip():
            errors.append("pack.yaml: persona dimension ids must be non-empty strings")
            continue
        if not isinstance(spec, dict):
            errors.append(f"pack.yaml: persona '{pid}' must be a mapping")
            continue
        lo, hi = spec.get("min", -3), spec.get("max", 3)
        default, speed = spec.get("default", 0), spec.get("speed", 1.0)
        for field, value in (("min", lo), ("max", hi), ("default", default),
                             ("speed", speed)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"pack.yaml: persona '{pid}' {field} must be numeric")
        if all(not isinstance(v, bool) and isinstance(v, (int, float))
               for v in (lo, hi, default)) and not lo <= default <= hi:
            errors.append(f"pack.yaml: persona '{pid}' default is outside bounds")
        if not isinstance(speed, bool) and isinstance(speed, (int, float)) and speed <= 0:
            errors.append(f"pack.yaml: persona '{pid}' speed must be positive")
        guidance = spec.get("guidance")
        if not isinstance(guidance, str) or not guidance.strip():
            errors.append(f"pack.yaml: persona '{pid}' guidance must be non-empty text")

    # -------------------------------- shared_knowledge entries (shared lore)
    if (pack.root / "knowledge.yaml").exists():
        warnings.append("knowledge.yaml: central knowledge pools were removed — "
                        "shared lore now lives in `shared_knowledge:` sections on the "
                        "entity it describes (character/item/location files); "
                        "this file is ignored")
    all_locs = {lid: pack.location(lid) for lid in loc_ids}
    entities = {}   # id -> (where-label, entity dict)
    for cid, c in chars.items():
        entities[cid] = (f"characters/{cid}", c)
    for iid, it in items.items():
        entities[iid] = (f"items/{iid}", it)
    for lid, lc in all_locs.items():
        entities[lid] = (f"locations/{lid}", lc)

    shared_scopes = set()
    for eid, (where, entity) in entities.items():
        if "about" in entity:
            errors.append(f"{where}: 'about' was renamed in spec 6; "
                          "use 'shared_knowledge'")
        ab = entity.get("shared_knowledge")
        if ab is None:
            continue
        if not isinstance(ab, list):
            errors.append(f"{where}: 'shared_knowledge' must be a list of entries")
            continue
        for k in ab:
            if not isinstance(k, dict) or not k.get("content"):
                errors.append(f"{where}: every shared_knowledge entry needs 'content'")
                continue
            scope = k.get("scope", "common")
            if not isinstance(scope, str) or not scope.strip():
                errors.append(f"{where}: shared_knowledge 'scope' must be a non-empty string")
                continue
            shared_scopes.add(scope)
            if "discloses" in k:
                errors.append(f"{where}: about 'discloses' was removed in spec 3; "
                              "use 'reveals'")
            if "reveals" in k and k["reveals"] not in facts:
                errors.append(f"{where}: shared_knowledge reveals unknown fact "
                              f"'{k['reveals']}'")
            for cond in (k.get("when") or []):
                # `self` is legal: it binds to the SUBJECT (this entity)
                _lint_condition(cond, f"{where} (shared_knowledge)", game_vars, facts,
                                tracks, errors, allow_self=True)

    known_scopes = {"common"}
    for cid, char in chars.items():
        if "knows" in char:
            errors.append(f"characters/{cid}: 'knows' was renamed in spec 6; "
                          "use 'knowledge_scopes'")
        kn = char.get("knowledge_scopes")
        if kn is None:
            continue
        if not isinstance(kn, list) or not all(
                isinstance(s, str) and s.strip() for s in kn):
            errors.append(f"characters/{cid}: 'knowledge_scopes' must be a list of scope names")
            continue
        for scope in kn:
            known_scopes.add(scope)
            if scope != "common" and scope not in shared_scopes:
                warnings.append(f"characters/{cid}: knowledge scope '{scope}' but no "
                                f"shared_knowledge entry uses it — dead subscription")
    for scope in shared_scopes:
        if scope not in known_scopes:
            warnings.append(f"shared knowledge scope '{scope}' is used but no character "
                            f"declares it in `knowledge_scopes` — those entries reach no one")

    # who can reveal what, best-case: own + shared knowledge entries
    # whose scope the character holds (relevance assumed best-case).
    # This is the DERIVED testimony source (replaces facts' revealed_by).
    ceiling_state = {"facts_learned": [], "flags": {}, "tracks": {}}
    revealers: dict[str, set] = {}   # fact id -> {character ids}
    for cid, char in chars.items():
        for k in char.get("knowledge", []) or []:
            if isinstance(k, dict) and "reveals" in k and all(
                    _best_case(c, facts, set(facts), tracks, game_vars, m,
                               ceiling_state, self_id=cid)
                    for c in (k.get("when") or [])):
                revealers.setdefault(k["reveals"], set()).add(cid)
        scopes = {"common"} | set(char.get("knowledge_scopes", []) or []
                                  if isinstance(char.get("knowledge_scopes"), list) else [])
        for eid, (_, entity) in entities.items():
            for k in entity.get("shared_knowledge", []) or []:
                if not isinstance(k, dict) or "reveals" not in k:
                    continue
                if k.get("scope", "common") not in scopes:
                    continue
                if all(_best_case(c, facts, set(facts), tracks, game_vars, m,
                                  ceiling_state, self_id=eid)
                       for c in (k.get("when") or [])):
                    revealers.setdefault(k["reveals"], set()).add(cid)

    # ------------------------------------------------------------- facts
    for fid, fact in facts.items():
        if "found_in" in fact:
            errors.append(f"facts.yaml: '{fid}' uses 'found_in', which was removed "
                          "in spec 4; define the source once in a location's "
                          "'search_reveals'")
        for req in fact.get("requires", []):
            if req not in facts:
                errors.append(f"facts.yaml: '{fid}' requires unknown fact '{req}'")
        if "revealed_by" in fact:
            warnings.append(f"facts.yaml: '{fid}' has 'revealed_by', which was "
                            f"removed — who can reveal a fact is now derived "
                            f"from knowledge/shared_knowledge entries that reveal it; "
                            f"the field is ignored")
        if "player_text" in fact:
            errors.append(f"facts.yaml: '{fid}' uses 'player_text', which was renamed "
                          "in spec 5; use 'journal_text'")
        if not fact.get("journal_text"):
            warnings.append(f"facts.yaml: '{fid}' has no journal_text "
                            "(journal will be blank)")
        for cond in fact.get("conditions", []) or []:
            _lint_condition(cond, f"facts.yaml:{fid}", game_vars, facts, tracks,
                            errors, allow_self=fid in revealers)

    # cycle check on requires graph
    cyc = _find_cycle({fid: fact.get("requires", []) for fid, fact in facts.items()})
    if cyc:
        errors.append(f"facts.yaml: circular requires chain: {' -> '.join(cyc)}")

    # ----------------------------------------------- locations/search reveals
    search_revealed_facts = set()
    for lid in loc_ids:
        loc = pack.location(lid)
        _lint_aliases(loc, f"locations/{lid}", errors)
        _lint_hints_flag(loc, f"locations/{lid}", errors)
        if "findables" in loc:
            errors.append(f"locations/{lid}: 'findables' was renamed in spec 4; "
                          "use 'search_reveals'")
        for f in loc.get("search_reveals", []):
            if "fact" in f:
                errors.append(f"locations/{lid}: findable 'fact' was removed in "
                              "spec 3; use 'reveals'")
            if f.get("reveals") not in facts:
                errors.append(f"locations/{lid}: findable references unknown fact "
                              f"'{f.get('reveals')}'")
            else:
                search_revealed_facts.add(f["reveals"])
            if not f.get("triggers"):
                warnings.append(f"locations/{lid}: findable '{f.get('reveals')}' has no "
                                f"triggers — it can never be discovered by search")
            if f.get("gives_item"):
                warnings.append(f"locations/{lid}: 'gives_item' was removed in "
                                f"spec 2 and is ignored (the host owns items)")

    # ------------------------------------------------------------- items
    for iid, item in items.items():
        _lint_aliases(item, f"items/{iid}", errors)
        if "short" in item:
            errors.append(f"items/{iid}: unused 'short' was removed in spec 6")
        for old in _REMOVED_ITEM:
            if old in item:
                warnings.append(f"items/{iid}: '{old}' was removed in spec 2 and "
                                f"is ignored (items are describable entities; "
                                f"the host owns movement and holders)")
        for er in item.get("examine_reveals", []) or []:
            if "fact" in er:
                errors.append(f"items/{iid}: examine_reveals 'fact' was removed in "
                              "spec 3; use 'reveals'")
            if er.get("reveals") not in facts:
                errors.append(f"items/{iid}: examine_reveals unknown fact "
                              f"'{er.get('reveals')}'")
            for cond in er.get("conditions", []) or []:
                _lint_condition(cond, f"items/{iid}", game_vars, facts, tracks,
                                errors, allow_self=False)
        if not item.get("triggers"):
            warnings.append(f"items/{iid}: no triggers — matching falls back "
                            f"to the item's name only")
    if player.get("inventory"):
        warnings.append("player.yaml: 'inventory' was removed in spec 2 and is "
                        "ignored (the host declares accessible items per call)")

    # -------------------------------------------------------- characters
    for cid, char in chars.items():
        _lint_aliases(char, f"characters/{cid}", errors)
        _lint_hints_flag(char, f"characters/{cid}", errors)
        if "short" in char:
            errors.append(f"characters/{cid}: 'short' was renamed in spec 6; "
                          "use 'summary'")
        if "pressure" in char:
            errors.append(f"characters/{cid}: 'pressure' was removed in spec 6; "
                          "use track_settings.<track>.guidance and track_prose")
        settings = char.get("track_settings")
        if default_track and not isinstance(settings, dict):
            warnings.append(f"characters/{cid}: no track_settings; '{default_track}' "
                            "uses manifest default start and speed 1.0")
            settings = {}
        for track, spec in (settings or {}).items():
            if track not in tracks:
                errors.append(f"characters/{cid}: track_settings references unknown "
                              f"track '{track}'")
                continue
            if not isinstance(spec, dict):
                errors.append(f"characters/{cid}: track_settings.{track} must be a mapping")
                continue
            start, speed = spec.get("start", tracks[track].get("default", 0)), spec.get("speed", 1.0)
            if isinstance(start, bool) or not isinstance(start, (int, float)):
                errors.append(f"characters/{cid}: track_settings.{track}.start must be numeric")
            elif not tracks[track].get("min", -3) <= start <= tracks[track].get("max", 3):
                errors.append(f"characters/{cid}: track_settings.{track}.start is outside track bounds")
            if isinstance(speed, bool) or not isinstance(speed, (int, float)) or speed <= 0:
                errors.append(f"characters/{cid}: track_settings.{track}.speed must be positive")
        for track in tracks:
            spec = settings.get(track) if isinstance(settings, dict) else None
            if not isinstance(spec, dict):
                warnings.append(f"characters/{cid}: no settings for track '{track}'; "
                                "uses manifest default start and speed 1.0")
            elif not spec.get("guidance") and not tracks[track].get("guidance"):
                warnings.append(f"characters/{cid}: track '{track}' has no guidance; "
                                "automatic adjudication will keep it unchanged")
            if char.get("track_prose", {}).get(track) is None:
                warnings.append(f"characters/{cid}: no track_prose for track "
                                f"'{track}' — it will read as 'Neutral.'")
        for k in char.get("knowledge", []):
            if "discloses" in k:
                errors.append(f"characters/{cid}: 'discloses' was removed in spec 3; "
                              "use 'reveals'")
            if "reveals" in k and k["reveals"] not in facts:
                errors.append(f"characters/{cid}: reveals unknown fact "
                              f"'{k['reveals']}'")
            for cond in (k.get("when") or []):
                _lint_condition(cond, f"characters/{cid}", game_vars, facts, tracks,
                                errors, allow_self=True)

    # ------------------------------------------------------ reachability
    item_sourced = set()
    for it in items.values():
        for er in it.get("examine_reveals", []) or []:
            item_sourced.add(er.get("reveals"))
    reachable = _reachable_facts(facts, search_revealed_facts | item_sourced,
                                 revealers, tracks, game_vars, m)
    for fid in facts:
        if fid not in reachable:
            errors.append(f"facts.yaml: '{fid}' is UNREACHABLE — no findable, "
                          f"examinable item, or knowledge/shared_knowledge entry that "
                          f"reveals it")

    return errors, warnings


def _lint_aliases(obj, where, errors):
    """`aliases` (characters/items/locations) must be a list of non-empty
    strings — they are matched/shown verbatim as alternate names."""
    al = obj.get("aliases")
    if al is None:
        return
    if not isinstance(al, list) or not all(
            isinstance(a, str) and a.strip() for a in al):
        errors.append(f"{where}: 'aliases' must be a list of non-empty strings")


def _lint_hints_flag(obj, where, errors):
    """Per-entity hint opt-out is a plain boolean; severity lives in the host's
    config, never in the pack."""
    if "hints" in obj and not isinstance(obj["hints"], bool):
        errors.append(f"{where}: 'hints' must be true or false (hint severity "
                      f"and thresholds are host config, not pack content)")


def _lint_condition(cond, where, game_vars, facts, tracks, errors, allow_self):
    if isinstance(cond, dict) and "fact_found" in cond:
        errors.append(f"{where}: 'fact_found' was renamed in spec 5; "
                      "use 'fact_learned'")
        return
    key = conditions.condition_key(cond) if isinstance(cond, dict) else None
    if key is None:
        errors.append(f"{where}: unknown condition {cond!r} (vocabulary: "
                      f"{sorted(conditions.KNOWN_KEYS)})")
        return
    if key == "not":
        inner = cond["not"]
        if isinstance(inner, dict) and conditions.condition_key(inner) == "not":
            errors.append(f"{where}: 'not' may not directly wrap another 'not'")
            return
        _lint_condition(inner, f"{where} (inside not)", game_vars, facts, tracks,
                        errors, allow_self)
        return
    if key == "var":
        if cond["var"] not in game_vars:
            errors.append(f"{where}: condition references undefined var '{cond['var']}'")
        if cond.get("is") == "self" and not allow_self:
            errors.append(f"{where}: 'self' has no meaning outside a character context")
    if key == "fact_learned" and cond["fact_learned"] not in facts:
        errors.append(f"{where}: condition references unknown fact "
                      f"'{cond['fact_learned']}'")
    # {flag: ...} is deliberately unchecked: flags belong to the HOST game
    # (injected per call / flags_file); a pack cannot know or misname them
    # statically, so any flag name is legal here.
    if key == "track_gte":
        spec = cond.get("track_gte", {})
        t = spec.get("track")
        if t not in tracks:
            errors.append(f"{where}: condition references undefined track '{t}'")
        elif spec.get("value", 0) > tracks[t].get("max", 0):
            errors.append(f"{where}: track_gte {spec.get('value')} exceeds track "
                          f"'{t}' max {tracks[t].get('max')} — can never be satisfied")


def _find_cycle(graph: dict) -> list | None:
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    def dfs(n, path):
        color[n] = GREY
        for nb in graph.get(n, []):
            if nb not in color:
                continue
            if color[nb] == GREY:
                return path + [n, nb]
            if color[nb] == WHITE:
                r = dfs(nb, path + [n])
                if r:
                    return r
        color[n] = BLACK
        return None
    for n in graph:
        if color[n] == WHITE:
            r = dfs(n, [])
            if r:
                return r
    return None


def _reachable_facts(facts, sourced_facts, revealers, tracks, game_vars, manifest):
    """Fixed-point reachability: a fact is reachable if its requires are all
    reachable AND it has a source (findable / examinable item / a knowledge
    entry that reveals it) AND its conditions are best-case satisfiable.
    Host flags (and their negations) are satisfiable by definition — the host
    controls them over time. For testimony, `self` in conditions is satisfied
    if ANY potential revealer satisfies it."""
    reachable = set()
    changed = True
    ceiling_state = {"facts_learned": [], "flags": {}, "tracks": {}}
    while changed:
        changed = False
        for fid, fact in facts.items():
            if fid in reachable:
                continue
            if not all(r in reachable for r in fact.get("requires", [])):
                continue
            via = revealers.get(fid, set())
            if fid not in sourced_facts and not via:
                continue
            selves = sorted(via) or [None]
            ok = all(
                any(_best_case(cond, facts, reachable, tracks, game_vars,
                               manifest, ceiling_state, self_id=s)
                    for s in selves)
                for cond in fact.get("conditions", []) or [])
            if ok:
                reachable.add(fid)
                changed = True
    return reachable


def _best_case(cond, facts, reachable, tracks, game_vars, manifest,
               ceiling_state, self_id):
    """Best-case satisfiability of one condition — the linter's twin of
    conditions.evaluate. Time-varying things (flags, tracks within bounds,
    negations of time-varying things) are assumed satisfiable at SOME moment."""
    key = conditions.condition_key(cond) if isinstance(cond, dict) else None
    if key == "track_gte":
        t = cond["track_gte"]
        return t.get("value", 0) <= tracks.get(t.get("track"), {}).get("max", 0)
    if key == "fact_learned":
        return cond["fact_learned"] in reachable
    if key == "flag":
        return True                       # host-controlled; assume best case
    if key == "var":
        return conditions.evaluate(cond, vars=game_vars, state=ceiling_state,
                                   manifest=manifest, self_id=self_id)
    if key == "not":
        inner = cond["not"]
        ikey = conditions.condition_key(inner) if isinstance(inner, dict) else None
        if ikey == "var":                 # vars are fixed: negation is decidable
            return not conditions.evaluate(inner, vars=game_vars,
                                           state=ceiling_state,
                                           manifest=manifest, self_id=self_id)
        return True                       # negations of time-varying gates: best case
    return False
