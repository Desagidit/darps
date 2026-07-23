"""Pack loading. A DARPS game is a directory ("pack") of declarative content;
this module is the only place that knows the on-disk layout.

Everything is re-read from disk per access — packs are small, and this makes
hot reload free while authoring.

Prompt resolution is layered: <pack>/prompts/<name>.txt if present, else the
engine default in darps/prompts/. Casual authors write zero prompts; power
authors can reskin every voice.
"""
from pathlib import Path
import re

import yaml

from . import conditions

ENGINE_PROMPTS = Path(__file__).resolve().parent / "prompts"


class Pack:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        if not (self.root / "pack.yaml").exists():
            raise FileNotFoundError(f"{self.root} is not a DARPS pack (no pack.yaml)")

    # ------------------------------------------------------------- raw loads
    def _yaml(self, rel: str):
        with (self.root / rel).open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def manifest(self) -> dict:
        return self._yaml("pack.yaml")

    def vars(self) -> dict:
        """Ground-truth variables (e.g. culprit). Engine-only; never enters
        any LLM context except via `when`-gated knowledge."""
        p = self.root / "vars.yaml"
        return self._yaml("vars.yaml") if p.exists() else {}

    def world(self) -> str:
        return (self.root / "world.md").read_text(encoding="utf-8")

    def facts(self) -> dict:
        return {f["id"]: f for f in (self._yaml("facts.yaml") or [])}


    def characters(self) -> dict:
        out = {}
        for p in sorted((self.root / "characters").glob("*.yaml")):
            c = self._yaml(f"characters/{p.name}")
            out[c["id"]] = c
        return out

    def items(self) -> dict:
        d = self.root / "items"
        out = {}
        if d.exists():
            for p in sorted(d.glob("*.yaml")):
                i = self._yaml(f"items/{p.name}")
                out[i["id"]] = i
        return out

    def player(self) -> dict:
        """Optional protagonist definition (player.yaml)."""
        p = self.root / "player.yaml"
        return self._yaml("player.yaml") if p.exists() else {}

    def location(self, loc_id: str) -> dict:
        return self._yaml(f"locations/{loc_id}.yaml")

    def location_ids(self) -> list[str]:
        return [p.stem for p in sorted((self.root / "locations").glob("*.yaml"))]

    # --------------------------------------------------------------- prompts
    def prompt(self, template_name: str, /, **vars) -> str:
        override = self.root / "prompts" / f"{template_name}.txt"
        source = override if override.exists() else ENGINE_PROMPTS / f"{template_name}.txt"
        template = source.read_text(encoding="utf-8")
        template = template.replace("{{", "\x00").replace("}}", "\x01")
        for key, value in vars.items():
            template = template.replace("{" + key + "}", str(value))
        return template.replace("\x00", "{").replace("\x01", "}")

    # ------------------------------------------------------------- rendering
    def effective_knowledge(self, char: dict, *, state: dict, game_vars: dict,
                            manifest: dict, tracks_enabled: bool = True) -> list:
        """The character's OWN knowledge entries that exist right now,
        `when:`-filtered with this character as `self`. Context isolation
        lives here — a gated-out entry never exists in the character's
        world."""
        return [k for k in char.get("knowledge", [])
                if conditions.all_hold(k.get("when"), vars=game_vars, state=state,
                                       manifest=manifest, self_id=char["id"],
                                       tracks_enabled=tracks_enabled)]

    def shared_knowledge_corpus(self, char: dict, entities: dict, *, state: dict,
                                 game_vars: dict, manifest: dict,
                                 tracks_enabled: bool = True) -> list:
        """Build every shared entry this character may know right now.

        Scope and conditions are applied before retrieval, so later selectors
        can inspect only secrecy-safe content. `self` in a shared entry binds
        to the subject entity.
        """
        scopes = set(char.get("knowledge_scopes", []) or [])
        if char.get("common_knowledge", True):
            scopes.add("common")
        out = []
        for eid, entity in entities.items():
            for k in entity.get("shared_knowledge", []) or []:
                if k.get("scope", "common") not in scopes:
                    continue
                if not conditions.all_hold(k.get("when"), vars=game_vars,
                                           state=state, manifest=manifest,
                                           self_id=eid,
                                           tracks_enabled=tracks_enabled):
                    continue
                out.append((eid, entity.get("name", eid), k))
        return out

    def retrieve_shared_knowledge(self, corpus: list, message: str, *,
                                  entities: dict, immediate_ids=(),
                                  selected_indexes=()) -> list:
        """Select relevant entries from an already secrecy-safe corpus."""
        immediate = set(immediate_ids)
        selected = {i for i in selected_indexes
                    if isinstance(i, int) and not isinstance(i, bool)
                    and 0 <= i < len(corpus)}
        query = _knowledge_terms(message)
        mentioned = match_entities(message, entities)
        out = []
        for index, (eid, name, entry) in enumerate(corpus):
            entity = entities.get(eid, {})
            document = " ".join([
                str(name), str(eid).replace("_", " "),
                " ".join(map(str, entity.get("aliases", []) or [])),
                str(entry.get("content", "")),
            ])
            if (eid in immediate or eid in mentioned or index in selected
                    or query & _knowledge_terms(document)):
                out.append((eid, name, entry))
        return out

    def knowledge_text(self, char: dict, *, state: dict, game_vars: dict,
                       manifest: dict, tracks_enabled: bool = True,
                       entries: list | None = None,
                       shared_knowledge: list | None = None) -> str:
        """Render a character's sheet for the LLM. The unified knowledge model:
        each entry may carry `when` (inclusion conditions) and/or `reveals` +
        `tell` (a disclosure policy linking to the gated fact web). Pass
        `entries` (from effective_knowledge) and `shared_knowledge`
        to avoid evaluating gates twice."""
        if entries is None:
            entries = self.effective_knowledge(
                char, state=state, game_vars=game_vars, manifest=manifest,
                tracks_enabled=tracks_enabled)
        parts = [
            f"Name: {char['name']} ({char.get('summary', '')})",
            f"Voice: {char.get('voice', '')}",
            f"Background: {char.get('background', '')}",
        ]
        for k in entries:
            parts.append(_render_entry(k, subject=None))
        for sid, sname, k in shared_knowledge or []:
            subject = "yourself" if sid == char["id"] else sname
            parts.append(_render_entry(k, subject=subject))
        return "\n\n".join(parts)

    def track_prose(self, char: dict, track: str, value: int) -> str:
        table = {int(k): v for k, v in char.get("track_prose", {}).get(track, {}).items()}
        if not table:
            return "Neutral."
        eligible = [k for k in table if k <= value]
        return table[max(eligible) if eligible else min(table)]


def _render_entry(k: dict, subject: str | None) -> str:
    """One knowledge/about entry as briefing prose. `subject` is None for the
    character's own knowledge, else the relevant entity's display name
    ('yourself' when the entry is about the speaker)."""
    if subject is None:
        prefix_know = "You know: "
        prefix_hide = "You are holding something back"
    elif subject == "yourself":
        prefix_know = "It is known about you: "
        prefix_hide = "Something is known about you that you keep quiet"
    else:
        prefix_know = f"You know about {subject}: "
        prefix_hide = f"You are holding something back about {subject}"
    if "reveals" in k:
        return (f"{prefix_hide} (fact id: {k['reveals']}): {k['content']} "
                + (f"Why you conceal it: {k['why']} " if k.get("why") else "")
                + (f"Behavioural tell: {k['tell']} " if k.get("tell") else "")
                + "Only disclose it if the conversation and your feelings toward "
                  "the player genuinely warrant it.")
    return f"{prefix_know}{k['content']}"


_KNOWLEDGE_STOPWORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "been", "but",
    "by", "did", "do", "does", "for", "from", "had", "has", "have", "he",
    "her", "him", "his", "how", "i", "in", "is", "it", "its", "me", "my",
    "of", "on", "or", "our", "she", "so", "that", "the", "their", "them",
    "they", "this", "to", "us", "was", "we", "were", "what", "when", "where",
    "which", "who", "why", "with", "you", "your",
}


def _knowledge_terms(text: str) -> set[str]:
    """Meaningful lowercase terms for conservative shared-lore retrieval."""
    return {token for token in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(token) >= 5 and token not in _KNOWLEDGE_STOPWORDS}


def match_entities(text: str, entities: dict) -> set:
    """All entity ids whose name/aliases appear in `text` — the
    deterministic MENTION detector for about-entry relevance. Collect-all
    sibling of match_item (which picks one best). No LLM: a nickname the
    alias list doesn't cover degrades to 'not brought up', never to a wrong
    answer."""
    hay = (text or "").lower()
    found = set()
    for eid, entity in entities.items():
        terms = ([entity.get("name", "")] + list(entity.get("aliases", []))
                 + [eid.replace("_", " ")])
        if any(t and t.strip().lower() in hay for t in map(str, terms)):
            found.add(eid)
    return found


def match_item(text: str, candidates: dict) -> str | None:
    """Deterministic noun -> item id matching over aliases + name
    words. `candidates` is {item_id: item_dict}; longest-term match wins so
    'letter opener' beats 'letter'. Aliases let an informal word the player
    reaches for ('desk' for a table) resolve to the canonical instance."""
    hay = (text or "").lower()
    best, best_len = None, 0
    for iid, item in candidates.items():
        terms = (list(item.get("aliases", []))
                 + [item.get("name", "").lower(), iid.replace("_", " ")])
        for t in terms:
            t = t.strip().lower()
            if t and t in hay and len(t) > best_len:
                best, best_len = iid, len(t)
    return best
