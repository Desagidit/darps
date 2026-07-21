"""The DARPS orchestrator — a conversation layer between a host game and an LLM.

The host supplies very limited info per call: who is being addressed (or what
is being examined), where we are, and the player's string. DARPS does the heavy
lifting: guardrails, alias resolution, gathering the right context slices
(character sheet with condition-gated knowledge, established canon, the
player's journal, disposition prose), calling the LLM, and validating every
proposed event before it touches narrative state.

DARPS does NOT coordinate the game. It moves no items, tracks no progress.
The host owns the world and signals progress through FLAGS (injected per call
and/or a flags file it keeps up to date); pack knowledge gates on those flags.

Two calls:
  talk(character_id, message, world=?, tone=?) -> a character speaks
  examine(target, message=?, world=?, tone=?) -> the narrator describes/reveals

Both return the result dict — the whole client boundary:
  {"speaker": str|None, "prose": str, "tone": str,
   "deltas": {"tracks", "persona", "facts_learned", "canon_added"}}
"""
from pathlib import Path

import yaml

from . import conditions, content, llm, state as state_mod, validate
from .content import Pack

HINT_STYLES = {"subtle", "pointed", "forthcoming"}


class Game:
    def __init__(self, cfg: dict, pack: Pack, state: dict):
        self.cfg = cfg          # runtime config: provider + behavior toggles
        self.pack = pack        # all game content lives here
        self.state = state      # narrative memory only (see state.py)
        self._ensure_track_starts()
        self._ensure_persona_defaults()

    # =================================================================== API
    def talk(self, character_id: str, message: str, *, world: dict | None = None,
             tone: str | None = None) -> dict:
        """The host names the conversant; DARPS never guesses a target."""
        manifest = self.pack.manifest()
        chars = self.pack.characters()
        if character_id not in chars:
            raise ValueError(f"unknown character id '{character_id}'")
        self.state["turn"] += 1
        before = self._snapshot()
        view = self._view(world, manifest)
        reading = self._classify_input(message, manifest, tone)
        persona = self._assess_persona(message, reading.get("tone", "neutral"), "talk")
        if reading.get("meta"):
            result = self._meta(manifest, reading)
            self._stage_persona(result, persona, "talk", message)
            return self._finish(result, manifest, before, meta=True)
        reading["track_shifts"] = self._assess_attitudes(
            chars[character_id], message, reading.get("tone", "neutral"))
        result = self._talk(chars[character_id], message, reading, manifest, view)
        self._stage_persona(result, persona, "talk", message)
        return self._finish(result, manifest, before)

    def talk_stream(self, character_id: str, message: str, *, world: dict | None = None,
                    tone: str | None = None):
        """Streaming twin of talk(): a generator of events for hosts that
        want prose to appear as it is generated.

            {"type": "text", "text": <chunk>}   zero or more, prose only
            {"type": "done", "result": <the full §12 result dict>}

        Only the PROSE streams. The fenced events block is withheld from the
        text stream (an incremental fence detector holds back a small tail so
        a partial fence can never leak), and `deltas` exist only
        after the complete reply passes the validation gate — they arrive
        with the final `done` event, whose `result.prose` is the canonical
        stripped prose (clients may reconcile, though it normally equals the
        streamed text). Same assembly, same gate, same state writes as
        talk(); streaming changes when the player sees words, never what
        becomes true."""
        manifest = self.pack.manifest()
        chars = self.pack.characters()
        if character_id not in chars:
            raise ValueError(f"unknown character id '{character_id}'")
        self.state["turn"] += 1
        before = self._snapshot()
        view = self._view(world, manifest)
        reading = self._classify_input(message, manifest, tone)
        persona = self._assess_persona(message, reading.get("tone", "neutral"), "talk")
        if reading.get("meta"):
            result = self._meta(manifest, reading)
            self._stage_persona(result, persona, "talk", message)
            result = self._finish(result, manifest, before, meta=True)
            yield {"type": "text", "text": result["prose"]}
            yield {"type": "done", "result": result}
            return
        reading["track_shifts"] = self._assess_attitudes(
            chars[character_id], message, reading.get("tone", "neutral"))
        ctx = self._prepare_talk(chars[character_id], message, reading, manifest, view)

        HOLD = 12   # never emit the last few chars until we know they aren't a fence
        pieces, emitted, suppressed = [], 0, False
        for chunk in llm.call_stream(self.cfg, ctx["prompt"],
                                     tag=f"character:{character_id}"):
            pieces.append(chunk)
            if suppressed:
                continue        # everything from the fence on is the events block
            acc = "".join(pieces)
            fence = acc.find("```")
            if fence != -1:
                out = acc[emitted:fence]
                suppressed = True
            else:
                out = acc[emitted:max(emitted, len(acc) - HOLD)]
            if out:
                emitted += len(out)
                yield {"type": "text", "text": out}
        raw = "".join(pieces)
        if not suppressed and emitted < len(raw):
            yield {"type": "text", "text": raw[emitted:]}   # flush the held tail

        result = self._apply_talk(ctx, message, raw, reading, manifest)
        self._stage_persona(result, persona, "talk", message)
        yield {"type": "done", "result": self._finish(result, manifest, before)}

    def examine(self, target: str, message: str = "", *,
                world: dict | None = None, tone: str | None = None) -> dict:
        """Narration/inspection — 'conversation' with the world. `target` may
        be an exact item id or a loose noun ('the desk'); aliases resolve it."""
        manifest = self.pack.manifest()
        message = message or f"examine {target}"
        self.state["turn"] += 1
        before = self._snapshot()
        view = self._view(world, manifest)
        reading = self._classify_input(message, manifest, tone)
        persona = self._assess_persona(message, reading.get("tone", "neutral"), "examine")
        if reading.get("meta"):
            result = self._meta(manifest, reading)
            self._stage_persona(result, persona, "examine", message)
            return self._finish(result, manifest, before, meta=True)
        result = self._narrate(target, message, reading, manifest, view)
        self._stage_persona(result, persona, "examine", message)
        return self._finish(result, manifest, before)

    def examine_stream(self, target: str, message: str = "", *,
                       world: dict | None = None, tone: str | None = None):
        """Streaming twin of examine(): prose chunks followed by one done event."""
        manifest = self.pack.manifest()
        message = message or f"examine {target}"
        self.state["turn"] += 1
        before = self._snapshot()
        view = self._view(world, manifest)
        reading = self._classify_input(message, manifest, tone)
        persona = self._assess_persona(message, reading.get("tone", "neutral"), "examine")
        if reading.get("meta"):
            result = self._meta(manifest, reading)
            self._stage_persona(result, persona, "examine", message)
            result = self._finish(result, manifest, before, meta=True)
            yield {"type": "text", "text": result["prose"]}
            yield {"type": "done", "result": result}
            return
        ctx = self._prepare_examine(target, message, reading, manifest, view)

        hold = 12
        pieces, emitted, suppressed = [], 0, False
        for chunk in llm.call_stream(self.cfg, ctx["prompt"], tag="narrator"):
            pieces.append(chunk)
            if suppressed:
                continue
            acc = "".join(pieces)
            fence = acc.find("```")
            if fence != -1:
                out = acc[emitted:fence]
                suppressed = True
            else:
                out = acc[emitted:max(emitted, len(acc) - hold)]
            if out:
                emitted += len(out)
                yield {"type": "text", "text": out}
        raw = "".join(pieces)
        if not suppressed and emitted < len(raw):
            yield {"type": "text", "text": raw[emitted:]}
        result = self._apply_examine(ctx, raw, reading)
        self._stage_persona(result, persona, "examine", message)
        yield {"type": "done", "result": self._finish(result, manifest, before)}

    # ------------------------------------------ host-authority writes (no LLM)
    def adjust_track(self, character_id: str, *, change: float | None = None,
                     value: float | None = None, track: str | None = None) -> dict:
        """Host-driven character-attitude change caused by the host game."""
        manifest = self.pack.manifest()
        if character_id not in self.pack.characters():
            raise ValueError(f"unknown character id '{character_id}'")
        if (change is None) == (value is None):
            raise ValueError("adjust_track needs exactly one of 'change' or 'value'")
        track = track or manifest.get("default_track", "disposition")
        bounds = manifest.get("tracks", {}).get(track)
        if bounds is None:
            raise ValueError(f"unknown track '{track}'")
        current = self.state["tracks"].get(track, {}).get(
            character_id, bounds.get("default", 0))
        new_value = float(value) if value is not None else current + float(change)
        new_value = max(bounds.get("min", -3), min(bounds.get("max", 3), new_value))
        self.state["tracks"].setdefault(track, {})[character_id] = new_value
        if self.cfg.get("autosave", True):
            state_mod.save(self.state, manifest["name"])
        return {"deltas": {"tracks": {track: {character_id: new_value}}}}

    def grant_fact(self, fact_id: str) -> dict:
        """Host-granted fact — the player learned it OUTSIDE conversation (a
        cutscene, a scripted scene, another game system). The host is the
        authority on its own story beats, so this bypasses the fact's gates;
        the id must exist in the pack. Idempotent: granting a held fact is a
        no-op. The fact enters the journal and all future LLM contexts,
        exactly as if earned in conversation."""
        facts = self.pack.facts()
        if fact_id not in facts:
            raise ValueError(f"unknown fact id '{fact_id}'")
        additions = self._learn_facts([fact_id], facts)
        if additions:
            self.state["fruitless_turns"] = 0
        if additions and self.cfg.get("autosave", True):
            state_mod.save(self.state, self.pack.manifest()["name"])
        return {"deltas": {"facts_learned": additions}}

    def add_canon(self, text: str) -> dict:
        """Host-authored narrative truth established outside an LLM turn."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("add_canon needs non-empty 'text'")
        text = " ".join(text.split())
        if len(text) > 500:
            raise ValueError("canon text must be at most 500 characters")
        added = []
        if self.cfg.get("canon", True) and text not in self.state["canon"]:
            self.state["canon"].append(text)
            added.append(text)
            if self.cfg.get("autosave", True):
                state_mod.save(self.state, self.pack.manifest()["name"])
        return {"deltas": {"canon_added": added}}

    # ------------------------------------------------------ turn scaffolding
    def _ensure_track_starts(self) -> None:
        """Seed authored starts after new-state creation or normalized restore."""
        if not self._tracks_on():
            return
        manifest = self.pack.manifest()
        for cid, char in self.pack.characters().items():
            settings = char.get("track_settings", {}) or {}
            for track, bounds in manifest.get("tracks", {}).items():
                start = (settings.get(track) or {}).get("start", bounds.get("default", 0))
                self.state.setdefault("tracks", {}).setdefault(track, {}).setdefault(cid, start)

    def _ensure_persona_defaults(self) -> None:
        """Fill declared persona defaults without overwriting restored scores."""
        self.state.setdefault("persona", {})
        for pid, spec in (self.pack.manifest().get("persona", {}) or {}).items():
            self.state["persona"].setdefault(pid, spec.get("default", 0))
        self.state.setdefault("persona_history", [])

    def _view(self, world: dict | None, manifest: dict) -> dict:
        """The effective state for THIS call: narrative memory + the host's
        world snapshot. Flags merge flags_file (host keeps it up to date;
        re-read every call) under per-call world flags. Never persisted."""
        world = world or {}
        flags = dict(self._file_flags())
        flags.update(world.get("flags") or {})
        return {**self.state, "flags": flags,
                "location": world.get("location") or manifest.get("start_location"),
                "_present": world.get("present"),
                "_carried": list(world.get("carried") or []),
                "_in_reach": list(world.get("in_reach") or []),
                # only restrict/assert scene objects if the host actually
                # described them; a world of just flags says nothing about items
                "_scene_given": ("carried" in world) or ("in_reach" in world)}

    def _file_flags(self) -> dict:
        path = self.cfg.get("flags_file")
        if not path or not Path(path).exists():
            return {}
        try:
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return {}   # a half-written file must not crash a turn

    def _snapshot(self) -> dict:
        return {"facts": len(self.state["facts_learned"]),
                "canon": len(self.state["canon"]),
                "persona": dict(self.state.get("persona", {})),
                "tracks": {t: dict(v) for t, v in self.state["tracks"].items()}}

    def _finish(self, result: dict, manifest: dict, before: dict,
                meta: bool = False) -> dict:
        persona_projected = result.pop("_persona_projected", None)
        persona_entry = result.pop("_persona_entry", None)
        if persona_projected is not None:
            self.state["persona"] = persona_projected
            if persona_entry:
                self.state["persona_history"].append(persona_entry)
                keep = int(self.cfg.get("persona_history_turns", 12))
                self.state["persona_history"] = self.state["persona_history"][-keep:]
        rel = result.pop("story_relevance", 1)
        learned_ids = self.state["facts_learned"][before["facts"]:]
        if learned_ids:
            self.state["fruitless_turns"] = 0
        elif rel >= 1 and not meta:
            self.state["fruitless_turns"] = self.state.get("fruitless_turns", 0) + 1
        track_deltas = {}
        for track, per_char in self.state["tracks"].items():
            for cid, val in per_char.items():
                if before["tracks"].get(track, {}).get(cid) != val:
                    track_deltas.setdefault(track, {})[cid] = val
        result["deltas"] = {
            "tracks": track_deltas,
            "persona": {p: value for p, value in self.state.get("persona", {}).items()
                        if before.get("persona", {}).get(p) != value},
            "facts_learned": [self._fact_delta(fid) for fid in learned_ids],
            "canon_added": self.state["canon"][before["canon"]:],
        }
        if self.cfg.get("autosave", True):
            state_mod.save(self.state, manifest["name"])
        return result

    def _relevant_entities(self, addressee_id: str, message: str, view: dict,
                           llm_mentions: list | None = None) -> dict:
        """The entities whose `shared_knowledge:` may enter this turn's
        briefing: the addressee, everything the host put in the scene
        (present characters, carried/in-reach items, the location), and
        anything the player's message MENTIONS by name/alias (deterministic).
        `llm_mentions` (opt-in resolver, ids already engine-validated) can
        only ADD relevance on top — fuzzy recall for misspellings and
        nicknames, never a veto. Bounded retrieval: entities outside this set
        contribute nothing this turn."""
        chars = self.pack.characters()
        items = self.pack.items()
        locations = {lid: self.pack.location(lid)
                     for lid in self.pack.location_ids()}
        relevant: dict = {}

        def add(eid, pool):
            if eid in pool and eid not in relevant:
                relevant[eid] = pool[eid]

        add(addressee_id, chars)
        for cid in view.get("_present") or []:
            add(cid, chars)
        for iid in view.get("_carried", []) + view.get("_in_reach", []):
            add(iid, items)
        add(view.get("location"), locations)
        mentioned = content.match_entities(message, {**chars, **items, **locations})
        for eid in mentioned | set(llm_mentions or []):
            for pool in (chars, items, locations):
                add(eid, pool)
        return relevant

    def _tracks_on(self) -> bool:
        return bool(self.cfg.get("tracks", True))

    def _canon_on(self) -> bool:
        return bool(self.cfg.get("canon", True))

    def _canon_context(self) -> str:
        if not self._canon_on():
            return "(canon building disabled; improvised details are not retained)"
        return "\n".join(f"- {c}" for c in self.state["canon"]) or "(none yet)"

    def _gate_kw(self, view: dict) -> dict:
        """Shared kwargs for every condition evaluation this call."""
        return {"vars": self.pack.vars(), "state": view,
                "manifest": self.pack.manifest(),
                "tracks_enabled": self._tracks_on()}

    # --------------------------------------------------------- input classifier
    def _classify_input(self, message: str, manifest: dict,
                        tone: str | None) -> dict:
        """The input classifier's duties: guardrails (meta/injection), tone
        (tone), topics, physics violations — and, when the host opts in
        (config `mention_resolver: true`), fuzzy entity-mention resolution for
        misspellings/nicknames the alias lists don't cover. NEVER targeting —
        the host already told us who or what. Skipped entirely when the host
        supplies `tone` and both guardrails and the resolver are off."""
        resolver = bool(self.cfg.get("mention_resolver", False))
        if tone is not None and not self.cfg.get("guardrails", True) \
                and not resolver:
            return {"tone": tone}
        mention_block, mention_field, known_ids = "", "", set()
        if resolver:
            # Names/aliases only — display strings; the classifier still
            # holds no secrets. Prompt-contract rule: the `mentions` field is
            # only requested when this roster accompanies it.
            lines = []
            for pool in (self.pack.characters(), self.pack.items(),
                         {lid: self.pack.location(lid)
                          for lid in self.pack.location_ids()}):
                for eid, e in pool.items():
                    known_ids.add(eid)
                    al = ", ".join(str(a) for a in e.get("aliases", []) or [])
                    lines.append(f"- {eid}: {e.get('name', eid)}"
                                 + (f" (also: {al})" if al else ""))
            mention_block = (
                "\nKnown entities (people, things, places). The player may "
                "misspell, nickname, or vaguely reference them:\n"
                + "\n".join(lines) + "\n")
            mention_field = (
                ',\n  "mentions": [<exact ids from the entity list that the '
                'input refers to, however loosely spelled; empty if none>]')
        prompt = self.pack.prompt(
            "classifier",
            player_label=manifest.get("player_label", "the player"),
            impossible_rules=manifest.get("impossible",
                                          "nothing beyond ordinary human ability"),
            mention_block=mention_block,
            mention_field=mention_field,
            player_text=message,
        )
        raw = llm.call(self.cfg, prompt, tag="classifier", classifier=True)
        reading = llm.extract_json(raw) or {}
        # LLM proposes, engine disposes: unknown/invented ids are stripped.
        reading["mentions"] = [m for m in (reading.get("mentions") or [])
                               if m in known_ids]
        if tone is not None:
            reading["tone"] = tone      # host's read wins; we keep the guardrail
        reading.setdefault("tone", "neutral")
        return reading

    def _meta(self, manifest: dict, reading: dict) -> dict:
        return {"speaker": None,
                "prose": manifest.get("meta_response",
                                      "That question belongs outside the story. "
                                      "The story is still here, waiting."),
                "tone": reading.get("tone", "neutral"),
                "story_relevance": 0}

    def _assess_attitudes(self, char: dict, message: str, tone: str) -> dict[str, int]:
        """Judge player conduct without seeing secrets or the generated reply."""
        if not self._tracks_on():
            return {}
        manifest = self.pack.manifest()
        tracks = manifest.get("tracks", {})
        settings = char.get("track_settings", {}) or {}
        guidance_lines = []
        for track, track_def in tracks.items():
            baseline = track_def.get("guidance", "")
            supplement = (settings.get(track) or {}).get("guidance", "")
            parts = []
            if baseline:
                parts.append(f"Pack-wide baseline: {baseline}")
            if supplement:
                parts.append(f"Character-specific supplement: {supplement}")
            if not parts:
                parts.append("No authored automatic-change criteria; return 0.")
            guidance_lines.append(f"- {track}: " + " ".join(parts))
        history = self.state.get("conversations", {}).get(char["id"], [])[-4:]
        player_history = "\n".join(f"- {h['player']}" for h in history) or "(none)"
        facts = self.pack.facts()
        player_facts = "\n".join(
            f"- {facts[f]['journal_text'].strip()}"
            for f in self.state.get("facts_learned", []) if f in facts) or "(none)"
        prompt = self.pack.prompt(
            "attitudes", name=char["name"],
            track_guidance="\n".join(guidance_lines),
            player_history=player_history, player_facts=player_facts,
            tone=tone, player_text=message)
        raw = llm.call(self.cfg, prompt, tag=f"attitudes:{char['id']}",
                       classifier=True)
        return validate.filter_track_shifts(llm.extract_json(raw) or {}, set(tracks))

    def _assess_persona(self, message: str, tone: str, input_kind: str) -> dict | None:
        """Project session-level player persona without exposing it to reply models."""
        dimensions = self.pack.manifest().get("persona", {}) or {}
        if not dimensions:
            return None
        guidance = "\n".join(
            f"- {pid}: {spec.get('guidance', '')}" for pid, spec in dimensions.items())
        history = self.state.get("persona_history", [])[-8:]
        history_text = "\n".join(
            f"- [{h.get('kind', 'input')}] {h.get('input', '')}" for h in history) or "(none)"
        player = self.pack.player()
        description = player.get("description") or self.pack.manifest().get(
            "player_label", "the player")
        facts = self.pack.facts()
        player_facts = "\n".join(
            f"- {facts[f]['journal_text'].strip()}"
            for f in self.state.get("facts_learned", []) if f in facts) or "(none)"
        prompt = self.pack.prompt(
            "persona", player_description=description,
            world_context=self.pack.world(), player_facts=player_facts,
            persona_guidance=guidance, persona_history=history_text,
            input_kind=input_kind, tone=tone, player_text=message)
        raw = llm.call(self.cfg, prompt, tag="persona", classifier=True)
        shifts = validate.filter_persona_shifts(llm.extract_json(raw) or {},
                                                 set(dimensions))
        projected = dict(self.state.get("persona", {}))
        for pid, spec in dimensions.items():
            value = projected.get(pid, spec.get("default", 0))
            value += shifts.get(pid, 0) * spec.get("speed", 1.0)
            projected[pid] = max(spec.get("min", -3), min(spec.get("max", 3), value))
        return projected

    @staticmethod
    def _stage_persona(result: dict, projected: dict | None,
                       input_kind: str, message: str) -> None:
        if projected is not None:
            result["_persona_projected"] = projected
            result["_persona_entry"] = {"kind": input_kind, "input": message}

    # ------------------------------------------------------------- character
    def _talk(self, char: dict, message: str, reading: dict,
              manifest: dict, view: dict) -> dict:
        ctx = self._prepare_talk(char, message, reading, manifest, view)
        raw = llm.call(self.cfg, ctx["prompt"], tag=f"character:{char['id']}")
        return self._apply_talk(ctx, message, raw, reading, manifest)

    def _prepare_talk(self, char: dict, message: str, reading: dict,
                      manifest: dict, view: dict) -> dict:
        """Everything before the model speaks: context assembly (the secrecy
        step) and the derived revealable set. Shared verbatim by the
        blocking and streaming paths so they cannot drift."""
        facts = self.pack.facts()
        game_vars = self.pack.vars()
        char_id = char["id"]
        projected_view = {**view,
                          "tracks": {t: dict(v) for t, v in view["tracks"].items()}}
        projected = {}
        attitude_prose = []
        char_settings = char.get("track_settings", {}) or {}
        for track, bounds in manifest.get("tracks", {}).items():
            value = self.state["tracks"].get(track, {}).get(
                char_id, bounds.get("default", 0))
            settings = char_settings.get(track, {}) or {}
            speed = settings.get("speed", 1.0)
            new_value = value
            if self._tracks_on():
                new_value += reading.get("track_shifts", {}).get(track, 0) * speed
                new_value = max(bounds.get("min", -3),
                                min(bounds.get("max", 3), new_value))
            projected[track] = new_value
            projected_view["tracks"].setdefault(track, {})[char_id] = new_value
            if self._tracks_on():
                attitude_prose.append(
                    f"{track.replace('_', ' ').title()}: "
                    f"{self.pack.track_prose(char, track, new_value)}")

        history = self.state["conversations"].get(char_id, [])
        history_text = "\n".join(
            f"Player: {h['player']}\n{char['name']}: {h['reply']}" for h in history
        ) or "(first exchange)"
        journal = [facts[f]["journal_text"].strip() for f in self.state["facts_learned"]]
        # One assembly serves both prompt and reveal authority: what the
        # briefing holds (own knowledge + about entries for this turn's
        # relevant entities) is exactly what the character MAY reveal.
        entries = self.pack.effective_knowledge(
            char, state=projected_view, game_vars=game_vars, manifest=manifest,
            tracks_enabled=self._tracks_on())
        relevant = self._relevant_entities(char_id, message, view,
                                           llm_mentions=reading.get("mentions"))
        shared = self.pack.shared_knowledge_entries(
            char, relevant, state=projected_view, game_vars=game_vars, manifest=manifest,
            tracks_enabled=self._tracks_on())
        revealable = ({k["reveals"] for k in entries if "reveals" in k}
                      | {k["reveals"] for _, _, k in shared if "reveals" in k})
        hint_text, slack = self._character_hint(char, facts, revealable)

        prompt = self.pack.prompt(
            "character",
            world=self._world(),
            in_reach=self._reach_line(view),
            player_label=manifest.get("player_label", "the player"),
            sheet=self.pack.knowledge_text(char, state=projected_view, game_vars=game_vars,
                                           manifest=manifest,
                                           tracks_enabled=self._tracks_on(),
                                           entries=entries, shared_knowledge=shared),
            attitude_prose=("\n\n".join(attitude_prose)
                               if self._tracks_on() else "Neutral."),
            canon=self._canon_context(),
            canon_instruction=(
                "Record up to three NEW concrete improvised biographical or world "
                "facts in canon_additions so they remain consistent later."
                if self._canon_on() else
                "Improvised details are ephemeral. Do not output canon_additions; they "
                "will not be remembered or treated as story truth."
            ),
            canon_additions_field=(
                '"canon_additions": [<up to 3 NEW concrete biographical/world facts '
                'you improvised, as short strings>],\n  '
                if self._canon_on() else ""
            ),
            facts_learned="\n".join(f"- {j}" for j in journal) or "(none)",
            history=history_text,
            tone=reading.get("tone", "neutral"),
            player_text=message,
            name=char["name"],
            hint_instruction=hint_text,
        )
        return {"prompt": prompt, "char": char, "facts": facts,
                "game_vars": game_vars, "view": projected_view,
                "projected": projected, "history": history,
                "revealable": revealable,
                "slack": slack}

    def _apply_talk(self, ctx: dict, message: str, raw: str, reading: dict,
                    manifest: dict) -> dict:
        """Everything after the model spoke: the validation gate and the
        narrative-only apply. Shared verbatim by blocking and streaming."""
        char, view = ctx["char"], ctx["view"]
        char_id = char["id"]
        prose = llm.strip_events_block(raw)
        events = validate.filter_character_events(
            llm.extract_json(raw), char_id, ctx["facts"], state=view,
            game_vars=ctx["game_vars"], manifest=manifest,
            revealable=ctx["revealable"], track_slack=ctx["slack"],
            tracks_enabled=self._tracks_on(),
            canon_enabled=self._canon_on(),
        )

        # apply — narrative deltas only
        if self._tracks_on():
            for track, value in ctx["projected"].items():
                self.state["tracks"].setdefault(track, {})[char_id] = value
        self._learn_facts(events["reveals"], ctx["facts"])
        self.state["canon"].extend(events["canon_additions"])
        ctx["history"].append({"player": message, "reply": prose})
        keep = int(self.cfg.get("history_turns", 12))
        self.state["conversations"][char_id] = ctx["history"][-keep:]

        return {"speaker": char["name"], "prose": prose,
                "tone": reading.get("tone", "neutral"),
                "story_relevance": events["story_relevance"]}

    # -------------------------------------------------------------- narrator
    def _narrate(self, target: str, message: str, reading: dict,
                 manifest: dict, view: dict) -> dict:
        ctx = self._prepare_examine(target, message, reading, manifest, view)
        raw = llm.call(self.cfg, ctx["prompt"], tag="narrator")
        return self._apply_examine(ctx, raw, reading)

    def _prepare_examine(self, target: str, message: str, reading: dict,
                         manifest: dict, view: dict) -> dict:
        loc = self.pack.location(view["location"])
        facts = self.pack.facts()
        game_vars = self.pack.vars()

        item_id, item = self._resolve_item(target, message, view)
        authorized = self._authorized_discoveries(target, message, reading,
                                                  loc, item_id, item, facts, view)
        if authorized:
            lines = "\n".join(
                f"- You MAY have {manifest.get('player_label','the player')} find fact "
                f"'{fid}' ({facts[fid]['journal_text'].strip()}) — weave the discovery "
                f"into the narration and include the id in reveals."
                for fid in authorized
            )
            discovery = "Authorized discoveries this turn:\n" + lines
        else:
            discovery = ("Nothing new is discoverable this turn. Narrate atmosphere, "
                         "scenery, or the action's outcome only; reveals MUST be empty.")

        loc_doc = (f"{loc['name']}: {loc['description']}\nScenery you may improvise "
                   f"around: {loc.get('scenery', '')}")
        if item is not None:
            loc_doc += (f"\nThe examined object (ground truth): "
                        f"{item.get('name', item_id)} — {item.get('description', '')}")

        prompt = self.pack.prompt(
            "narrator",
            world=self._world(),
            in_reach=self._reach_line(view),
            player_label=manifest.get("player_label", "the player"),
            location_doc=loc_doc,
            canon=self._canon_context(),
            facts_learned=", ".join(self.state["facts_learned"]) or "none",
            player_text=message,
            tone=reading.get("tone", "neutral"),
            impossible=bool(reading.get("impossible", False)),
            discovery_instruction=discovery,
            hint_instruction=self._narrator_hint(loc, facts, game_vars, view),
        )
        return {"prompt": prompt, "authorized": authorized, "facts": facts}

    def _apply_examine(self, ctx: dict, raw: str, reading: dict) -> dict:
        prose = llm.strip_events_block(raw)
        events = validate.filter_narrator_events(llm.extract_json(raw), ctx["authorized"])
        self._learn_facts(events["reveals"], ctx["facts"])
        return {"speaker": None, "prose": prose,
                "tone": reading.get("tone", "neutral"),
                "story_relevance": events["story_relevance"]}

    def _resolve_item(self, target: str, message: str, view: dict):
        """Alias resolution: exact id first, then deterministic matching over
        triggers/aliases/name. With a world snapshot, only items the host says
        are carried or in reach are candidates; without one (dev harness),
        every pack item is."""
        items = self.pack.items()
        if view.get("_scene_given"):
            reachable = set(view["_carried"]) | set(view["_in_reach"])
            items = {i: it for i, it in items.items() if i in reachable}
        if target in items:
            return target, items[target]
        iid = content.match_item(f"{target} {message}", items)
        return (iid, items[iid]) if iid else (None, None)

    def _authorized_discoveries(self, target, message, reading, loc,
                                item_id, item, facts, view) -> list[str]:
        """Engine-side matching of an examination against location search reveals and item
        examine_reveals, gated by the fact web. The LLM never decides this."""
        if reading.get("impossible"):
            return []
        gate_kw = self._gate_kw(view)
        haystack = " ".join([target.lower(), message.lower(),
                             " ".join(reading.get("topics") or []).lower()])
        approved = []
        for f in loc.get("search_reveals", []):
            fact = facts.get(f["reveals"])
            if fact and any(t in haystack for t in f.get("triggers", [])):
                if validate.fact_reveal_allowed(fact, state=view,
                                                game_vars=gate_kw["vars"],
                                                manifest=gate_kw["manifest"],
                                                tracks_enabled=gate_kw["tracks_enabled"]):
                    approved.append(fact["id"])
        if item is not None:
            for er in item.get("examine_reveals", []) or []:
                fact = facts.get(er["reveals"])
                if fact and fact["id"] not in approved \
                        and conditions.all_hold(er.get("conditions"), **gate_kw) \
                        and validate.fact_reveal_allowed(
                            fact, state=view, game_vars=gate_kw["vars"],
                            manifest=gate_kw["manifest"],
                            tracks_enabled=gate_kw["tracks_enabled"]):
                    approved.append(fact["id"])
        return approved

    # ----------------------------------------------------------------- hints
    def _hint_cfg(self) -> dict | None:
        """Simplified pacing: one threshold, one style, configured by the HOST
        (config.yaml `hints: {after_turns: N, style: subtle|pointed|forthcoming}`).
        Absent/false = off. Entities opt out with `hints: false` in their file."""
        h = self.cfg.get("hints")
        if not isinstance(h, dict):
            return None
        style = h.get("style", "subtle")
        if style not in HINT_STYLES:
            style = "subtle"
        if self.state.get("fruitless_turns", 0) < h.get("after_turns", 6):
            return None
        return {"style": style}

    def _character_hint(self, char: dict, facts: dict, revealable: set):
        h = self._hint_cfg()
        if h is None or char.get("hints", True) is False:
            return "", 0
        candidate = None
        for fid in sorted(revealable):
            fact = facts.get(fid)
            if fact and fid not in self.state["facts_learned"] \
                    and all(r in self.state["facts_learned"]
                            for r in fact.get("requires", [])):
                candidate = fact
                break
        if candidate is None:
            return "", 0
        subject = candidate.get("journal_text", "").strip()[:120]
        if h["style"] == "subtle":
            return ("PACING NOTE: progress has slowed. Let your behavioural tell "
                    "about what you are holding back show a little more plainly "
                    "this turn. Do NOT reveal it."), 0
        if h["style"] == "pointed":
            return (f"PACING NOTE: progress has stalled. Steer the conversation "
                    f"near the subject you are holding back (it concerns: "
                    f"{subject}...). Make your discomfort unmistakable — invite "
                    f"the right question. Do NOT reveal it unprompted."), 0
        return ("PACING NOTE: the player is badly stuck. If the conversation "
                "gives any plausible opening, your character relents: you may "
                "volunteer what you have been holding back, in your own manner."), 1

    def _narrator_hint(self, loc, facts, game_vars, view) -> str:
        h = self._hint_cfg()
        if h is None or loc.get("hints", True) is False:
            return ""
        found = None
        for f in loc.get("search_reveals", []):
            fact = facts.get(f["fact"])
            if fact and validate.fact_reveal_allowed(
                    fact, state=view, game_vars=game_vars,
                    manifest=self.pack.manifest(),
                    tracks_enabled=self._tracks_on()):
                found = f
                break
        if found is None:
            return ""
        where = found.get("where", "somewhere nearby")
        if h["style"] == "subtle":
            return (f"PACING NOTE: progress has slowed. Let the narration's eye "
                    f"linger briefly on {where} — atmosphere only, no discovery.")
        if h["style"] == "pointed":
            return (f"PACING NOTE: progress has stalled. Give {where} a pointed "
                    f"sensory detail that would snag an attentive eye. Do not "
                    f"reveal its meaning.")
        return (f"PACING NOTE: the player is badly stuck. Have their instincts "
                f"all but tug them toward {where} — one step short of making "
                f"the discovery for them.")

    # ---------------------------------------------------------------- shared
    def _world(self) -> str:
        w = self.pack.world()
        player = self.pack.player()
        if player.get("description"):
            w += ("\n\n=== THE PLAYER CHARACTER ===\n" + player["description"].strip()
                  + "\nNarration and characters treat the player as this person; "
                    "the player has no abilities or possessions beyond what is "
                    "established here and in what the scene says they carry.")
        return w

    def _reach_line(self, view: dict) -> str:
        """Ground-truth 'what objects are part of this scene' line, from the
        host's snapshot. Without a snapshot (dev harness), stay silent rather
        than invent a world DARPS doesn't own."""
        if not view.get("_scene_given"):
            return "(the host game did not specify; do not dwell on objects)"
        items = self.pack.items()
        ids = list(dict.fromkeys(view["_carried"] + view["_in_reach"]))
        named = [f"{items[i].get('name', i)} (id: {i})" for i in ids if i in items]
        return ", ".join(named) if named else "nothing of note"

    def _learn_facts(self, reveal_ids: list[str], facts: dict) -> list[dict]:
        additions = []
        for fid in reveal_ids:
            if fid not in self.state["facts_learned"]:
                self.state["facts_learned"].append(fid)
                additions.append(self._fact_delta(fid, facts))
        return additions

    def _fact_delta(self, fact_id: str, facts: dict | None = None) -> dict:
        fact = (facts or self.pack.facts())[fact_id]
        return {"id": fact_id, "journal_text": fact["journal_text"].strip()}
