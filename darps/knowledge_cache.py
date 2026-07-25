"""Inspectable, optional routing catalogues for static common knowledge.

The catalogue is never narrative authority. It contains compact routing text
for common, ungated shared-knowledge entries; the orchestrator always maps a
selection back to the exact live YAML entry before briefing or reveal use.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import yaml

from . import llm


FORMAT = 2
DEFAULT_FILENAME = "knowledge-cache.yaml"
_LEVEL_WORDS = {1: 40, 2: 20, 3: 12}


class KnowledgeCacheError(ValueError):
    """A catalogue is unusable; callers should fall back to live content."""


def _entities(pack) -> dict:
    entities = {}
    entities.update(pack.characters())
    entities.update(pack.items())
    for location_id in pack.location_ids():
        entities[location_id] = pack.location(location_id)
    return entities


def entry_fingerprint(subject_id: str, entry: dict) -> str:
    """Stable identity for mapping a route back to an exact live entry."""
    payload = json.dumps(
        {"subject": subject_id, "entry": entry},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def common_ungated_sources(pack) -> list[dict]:
    """Return the immutable subset eligible for compilation."""
    sources = []
    for subject_id, entity in sorted(_entities(pack).items()):
        for entry in entity.get("shared_knowledge", []) or []:
            if entry.get("scope", "common") != "common":
                continue
            if entry.get("when"):
                continue
            sources.append({
                "source": entry_fingerprint(subject_id, entry),
                "subject": subject_id,
                "entry": entry,
            })
    return sources


def _source_hash(sources: list[dict]) -> str:
    payload = json.dumps(
        sources, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_hash(pack) -> str:
    """Hash the exact authoritative source represented by a catalogue."""
    return _source_hash(common_ungated_sources(pack))


def _compression_cfg(cfg: dict, setting) -> dict:
    cache_cfg = setting if isinstance(setting, dict) else {}
    compression = cache_cfg.get("compression", {}) or {}
    if not isinstance(compression, dict):
        raise ValueError("knowledge_cache.compression must be a mapping")
    compression_provider = compression.get("provider")
    provider_explicit = bool(compression_provider)
    provider = compression_provider or cfg.get("provider", "openai")
    model = compression.get("model") or cfg.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(
            "knowledge cache compilation needs compression.model or model")
    base_url = compression.get("base_url") or (
        None if provider_explicit else cfg.get("base_url"))
    return {
        **cfg,
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "temperature": compression.get("temperature", 0.2),
        "max_tokens": compression.get("max_tokens", 16000),
    }


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def _semantic_routes(pack, sources: list[dict], entities: dict, *,
                     cfg: dict, setting, level: int) -> tuple[list[str], dict]:
    compile_cfg = _compression_cfg(cfg, setting)
    budget = _LEVEL_WORDS[level]
    candidates = [
        {
            "id": index,
            "subject": source["subject"],
            "name": entities[source["subject"]].get(
                "name", source["subject"]),
            "content": source["entry"].get("content", ""),
        }
        for index, source in enumerate(sources)
    ]
    prompt = pack.prompt(
        "knowledge_compile",
        level=level,
        word_budget=budget,
        candidates=json.dumps(candidates, ensure_ascii=False, indent=2),
    )
    raw = llm.call(compile_cfg, prompt, tag="knowledge-compile")
    proposed = (llm.extract_json(raw) or {}).get("routes")
    if not isinstance(proposed, list):
        raise KnowledgeCacheError(
            "compression model did not return a routes list")
    routes = {}
    for item in proposed:
        if not isinstance(item, dict):
            raise KnowledgeCacheError(
                "compression model returned a malformed route")
        route_id = item.get("id")
        routing = item.get("routing")
        if not isinstance(route_id, int) or isinstance(route_id, bool) \
                or not isinstance(routing, str) or not routing.strip():
            raise KnowledgeCacheError(
                "compression model returned a malformed route")
        if route_id in routes:
            raise KnowledgeCacheError(
                f"compression model returned duplicate route id {route_id}")
        routing = " ".join(routing.split())
        if _word_count(routing) > budget:
            raise KnowledgeCacheError(
                f"route {route_id} exceeds the {budget}-word level-{level} budget")
        routes[route_id] = routing
    expected = set(range(len(sources)))
    if set(routes) != expected:
        raise KnowledgeCacheError(
            "compression model did not return exactly one route per source")
    compiler = {
        "provider": compile_cfg.get("provider"),
        "model": compile_cfg.get("model"),
        "temperature": compile_cfg.get("temperature"),
        "max_tokens": compile_cfg.get("max_tokens"),
    }
    return [routes[index] for index in range(len(sources))], compiler


def compile_catalogue(pack, cfg: dict, *, setting=None,
                      level: int = 2) -> dict:
    """Build a model-compressed, human-inspectable routing catalogue."""
    if level not in (0, 1, 2, 3):
        raise ValueError("knowledge cache level must be 0, 1, 2, or 3")
    sources = common_ungated_sources(pack)
    entities = _entities(pack)
    if level == 0:
        routes = [
            " ".join(str(source["entry"].get("content", "")).split())
            for source in sources
        ]
        compiler = {"provider": None, "model": None}
    elif sources:
        routes, compiler = _semantic_routes(
            pack, sources, entities, cfg=cfg, setting=setting, level=level)
    else:
        routes, compiler = [], {"provider": None, "model": None}
    entries = []
    for source, routing in zip(sources, routes):
        subject_id = source["subject"]
        entity = entities[subject_id]
        entries.append({
            "source": source["source"],
            "subject": subject_id,
            "name": entity.get("name", subject_id),
            "routing": routing,
        })
    return {
        "format": FORMAT,
        "source_hash": _source_hash(sources),
        "level": level,
        "compiler": compiler,
        "entries": entries,
    }


def write_catalogue(pack, cfg: dict, *, setting=None,
                    output: str | Path | None = None, level: int = 2) -> Path:
    """Compile and atomically write the catalogue beside the pack."""
    if output is not None:
        path = Path(output)
    elif isinstance(setting, str):
        path = Path(setting)
    elif isinstance(setting, dict):
        path = Path(setting.get("path") or DEFAULT_FILENAME)
    else:
        path = Path(DEFAULT_FILENAME)
    if not path.is_absolute():
        path = pack.root / path
    catalogue = compile_catalogue(
        pack, cfg, setting=setting, level=level)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(
        catalogue, sort_keys=False, allow_unicode=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=path.parent, delete=False,
                prefix=f".{path.name}.", suffix=".tmp") as handle:
            temporary = Path(handle.name)
            handle.write(rendered)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path


def _configured_path(pack, setting) -> Path | None:
    if setting is False or setting is None:
        return None
    if setting is True:
        return pack.root / DEFAULT_FILENAME
    if isinstance(setting, str):
        path = Path(setting)
        return path if path.is_absolute() else pack.root / path
    if isinstance(setting, dict):
        if not setting.get("enabled", True):
            return None
        path = Path(setting.get("path", DEFAULT_FILENAME))
        return path if path.is_absolute() else pack.root / path
    raise KnowledgeCacheError(
        "knowledge_cache must be false, true, a path, or a mapping")


def load_catalogue(pack, setting) -> tuple[dict[str, str], Path | None]:
    """Load and validate routes, or raise for the orchestrator to fall back."""
    path = _configured_path(pack, setting)
    if path is None:
        return {}, None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise KnowledgeCacheError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise KnowledgeCacheError(f"{path} has an unsupported format")
    if data.get("level") not in (0, 1, 2, 3):
        raise KnowledgeCacheError(f"{path} has an invalid compression level")
    sources = common_ungated_sources(pack)
    if data.get("source_hash") != _source_hash(sources):
        raise KnowledgeCacheError(
            f"{path} is stale; run `darps compile-knowledge {pack.root}`")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise KnowledgeCacheError(f"{path} entries must be a list")
    routes = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise KnowledgeCacheError(f"{path} contains a malformed entry")
        fingerprint = entry.get("source")
        routing = entry.get("routing")
        if not isinstance(fingerprint, str) or not isinstance(routing, str) \
                or not routing.strip():
            raise KnowledgeCacheError(f"{path} contains a malformed route")
        routes[fingerprint] = routing.strip()
    expected = {source["source"] for source in sources}
    if set(routes) != expected:
        raise KnowledgeCacheError(f"{path} does not cover its hashed sources")
    return routes, path
