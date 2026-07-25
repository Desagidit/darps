#!/usr/bin/env python3
"""DARPS CLI.

  darps serve <pack>     the real interface: localhost HTTP for a host game
  darps validate <pack>  static pack linting
  darps compile-knowledge <pack>  build an inspectable common-lore catalogue
  darps new <dir>        scaffold a pack
  darps play <pack>      DEV HARNESS: talk/examine with explicit addressing —
                         a stand-in for a host game, not a text adventure.
                         @<char id> <message>   talk to a character
                         x <target> [words...]  examine something
                         /flag <name>           toggle a host flag (injected)
                         /adjust <character> <±n> host-driven track change
                         /grant <fact id>       host-granted fact (bypasses gates)
                         /canon <text>          host-authored narrative canon
                         /journal /persona /state /new /quit

Run as `python -m darps ...` or via the installed entry point."""
import argparse
import json
import sys
from pathlib import Path

import yaml

from . import (env, knowledge_cache, lint as lint_mod, llm, scaffold,
               state as state_mod)
from .content import Pack
from .orchestrator import Game


def load_cfg(path: str) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_validate(args) -> int:
    pack = Pack(args.pack)
    errors, warnings = lint_mod.lint(pack)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    n = pack.manifest().get("name", args.pack)
    if errors:
        print(f"\n{n}: {len(errors)} error(s), {len(warnings)} warning(s) — pack is not usable.")
        return 1
    print(f"\n{n}: OK ({len(warnings)} warning(s)).")
    return 0


def cmd_new(args) -> int:
    root = scaffold.scaffold(args.dir)
    print(f"Scaffolded pack in {root}/")
    print(f"Next: edit the YAML, then `darps validate {root}` and `darps serve {root}`")
    return 0


def cmd_compile_knowledge(args) -> int:
    env.load()
    cfg = load_cfg(args.config)
    pack = Pack(args.pack)
    errors, _ = lint_mod.lint(pack)
    if errors:
        print(f"Pack has {len(errors)} validation error(s); "
              f"run `darps validate {args.pack}`.")
        return 1
    try:
        path = knowledge_cache.write_catalogue(
            pack, cfg, setting=cfg.get("knowledge_cache"),
            output=args.output, level=args.level)
        catalogue = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, llm.ProviderError) as exc:
        print(f"Could not compile knowledge: {exc}")
        return 1
    print(f"Compiled {len(catalogue['entries'])} common, ungated routes "
          f"at level {args.level} into {path}")
    compiler = catalogue.get("compiler", {})
    if compiler.get("model"):
        print(f"Compression model: {compiler.get('provider')}/"
              f"{compiler['model']} (one author-time call)")
    else:
        print("Compression model: none (level 0 full text)")
    return 0


def cmd_serve(args) -> int:
    env.load()
    cfg = load_cfg(args.config)
    pack = Pack(args.pack)
    errors, _ = lint_mod.lint(pack)
    if errors:
        print(f"Pack has {len(errors)} validation error(s); run `darps validate {args.pack}`.")
        return 1
    from . import server
    server.serve(cfg, pack, host=args.host, port=args.port)
    return 0


def cmd_play(args) -> int:
    """Dev harness: play the host game's role by hand."""
    env.load()
    cfg = load_cfg(args.config)
    pack = Pack(args.pack)
    errors, _ = lint_mod.lint(pack)
    if errors:
        print(f"Pack has {len(errors)} validation error(s); run `darps validate {args.pack}`.")
        return 1
    manifest = pack.manifest()
    try:
        state = state_mod.load_or_new(pack)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Save is incompatible or malformed: {exc}")
        return 1
    game = Game(cfg, pack, state)
    flags: dict[str, bool] = {}
    chars = pack.characters()

    print(f"\n=== {manifest['name']} (dev harness) ===")
    print(f"characters: {', '.join(chars)}")
    print("@<id> <msg> | x <target> [msg] | /flag <name> | /adjust <character> <±n> | "
          "/grant <fact> | /canon <text> | /journal /persona /state /new /quit\n")

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text == "/new":
            state = state_mod.new_state(manifest)
            game = Game(cfg, pack, state)
            state_mod.save(state, manifest["name"])
            flags.clear()
            print("(fresh session)")
            continue
        if text == "/state":
            print(json.dumps({k: v for k, v in state.items() if k != "conversations"},
                             indent=2, ensure_ascii=False))
            print(f"host flags: {flags or '(none)'}")
            continue
        if text == "/journal":
            facts = pack.facts()
            for fid in state["facts_learned"]:
                print(f"- {facts[fid]['journal_text'].strip()}")
            if not state["facts_learned"]:
                print("(empty)")
            continue
        if text == "/persona":
            print(json.dumps(state.get("persona", {}), indent=2,
                             ensure_ascii=False))
            continue
        if text.startswith("/flag "):
            name = text[len("/flag "):].strip()
            flags[name] = not flags.get(name, False)
            print(f"(flag {name} = {flags[name]})")
            continue
        if text.startswith("/adjust "):
            try:
                _, character, amount = text.split(None, 2)
                out = game.adjust_track(character, change=int(amount))
                print(f"({out['deltas']['tracks']})")
            except (ValueError, TypeError) as exc:
                print(f"(usage: /adjust <character> <±n> — {exc})")
            continue
        if text.startswith("/grant "):
            try:
                out = game.grant_fact(text[len("/grant "):].strip())
                learned = out["deltas"]["facts_learned"]
                print(f"(granted: {[f['id'] for f in learned] or 'already held'})")
            except ValueError as exc:
                print(f"({exc})")
            continue
        if text.startswith("/canon "):
            try:
                out = game.add_canon(text[len("/canon "):])
                print(f"(canon added: {out['deltas']['canon_added'] or 'none'})")
            except ValueError as exc:
                print(f"({exc})")
            continue

        world = {"flags": dict(flags)}
        try:
            if text.startswith("@"):
                character, _, msg = text[1:].partition(" ")
                result = game.talk(character, msg.strip() or "...", world=world)
            elif text.split(" ", 1)[0] in ("x", "examine"):
                rest = text.split(" ", 1)[1] if " " in text else ""
                target, _, msg = rest.partition(" ")
                if not target:
                    print("usage: x <target> [message]")
                    continue
                result = game.examine(target, msg.strip(), world=world)
            else:
                print("address someone (@butler ...) or examine something (x desk)")
                continue
        except ValueError as exc:
            print(f"({exc})")
            continue
        except Exception as exc:
            print(f"(engine error: {exc})")
            continue
        print()
        if result["speaker"]:
            print(f"—— {result['speaker']} ——")
        print(result["prose"])
        for fact in result["deltas"]["facts_learned"]:
            print(f"\n  [Journal updated] {fact['journal_text']}")
        print()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="darps",
                                description="Dynamic Agentic Roleplaying System — "
                                            "a conversation layer between a game and an LLM")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("play", help="dev harness: drive the API by hand")
    sp.add_argument("pack")
    sp.add_argument("--config", default="config.yaml")
    sp.set_defaults(fn=cmd_play)
    sv = sub.add_parser("validate", help="statically validate a pack")
    sv.add_argument("pack")
    sv.set_defaults(fn=cmd_validate)
    sn = sub.add_parser("new", help="scaffold a new pack")
    sn.add_argument("dir")
    sn.set_defaults(fn=cmd_new)
    sk = sub.add_parser(
        "compile-knowledge",
        help="compile common ungated shared knowledge into a routing catalogue")
    sk.add_argument("pack")
    sk.add_argument(
        "--output",
        help="output path (default: knowledge-cache.yaml in the pack)")
    sk.add_argument(
        "--config", default="config.yaml",
        help="host config containing the compression model (default: config.yaml)")
    sk.add_argument(
        "--level", type=int, choices=(0, 1, 2, 3), default=2,
        help="0 full text; semantic route budgets: 1=40, 2=20, 3=12 words")
    sk.set_defaults(fn=cmd_compile_knowledge)
    ss = sub.add_parser("serve", help="run the localhost HTTP layer for a host game")
    ss.add_argument("pack")
    ss.add_argument("--config", default="config.yaml")
    ss.add_argument("--host", default="127.0.0.1")
    ss.add_argument("--port", type=int, default=8080)
    ss.set_defaults(fn=cmd_serve)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
