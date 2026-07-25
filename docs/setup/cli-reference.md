# Command-line tools

DARPS includes commands for creating and validating packs, testing them
interactively, compiling large knowledge catalogues, and running the HTTP
sidecar used by a host game.

Commands can be invoked through the installed entry point:

```bash
darps <command> [options]
```

Or directly through Python:

```bash
python -m darps <command> [options]
```

The two forms are equivalent. The examples below use `darps` for brevity.
Run `darps --help` or `darps <command> --help` for the options supported by
the installed code.

## Command summary

| Command | Purpose | Model call? |
|---|---|---:|
| `darps new <dir>` | Scaffold a new pack | No |
| `darps validate <pack>` | Validate pack structure, references, gates, and reachability | No |
| `darps play <pack>` | Drive the conversation API through an interactive development harness | Yes |
| `darps compile-knowledge <pack>` | Build an optional common-knowledge routing catalogue | Levels 1–3 only |
| `darps serve <pack>` | Run the localhost HTTP sidecar for a host game | When an API request requires one |

## `darps new`

Create a complete starter pack:

```bash
darps new packs/my-game
```

### Arguments

| Argument | Required | Meaning |
|---|---:|---|
| `dir` | Yes | Destination directory for the new pack |

The command creates a commented, valid example containing a manifest, world
bible, player definition, facts, characters, locations, items, and variables.
It creates parent directories when necessary.

It does not overwrite an existing pack. If `<dir>/pack.yaml` already exists,
the command stops with an error.

After scaffolding:

```bash
darps validate packs/my-game
darps play packs/my-game
```

## `darps validate`

Statically validate a pack without calling a model:

```bash
darps validate packs/my-game
```

### Arguments

| Argument | Required | Meaning |
|---|---:|---|
| `pack` | Yes | Pack directory to validate |

Validation checks the current pack contract, including:

- required files and fields;
- entity and fact references;
- condition syntax;
- fact prerequisite cycles;
- discovery and testimony sources;
- best-case fact reachability;
- track, persona, knowledge, and examination schemas;
- removed or counterintuitive legacy fields.

Warnings are printed as `WARN`; errors are printed as `ERROR`. A valid pack
returns exit code `0`:

```text
My Game: OK (0 warning(s)).
```

A pack with errors returns exit code `1`, making this command suitable for CI:

```yaml
- name: Validate DARPS pack
  run: python -m darps validate packs/my-game
```

Validation proves structural consistency and static reachability. It does not
judge prose quality or replace playtesting.

## `darps play`

Open the interactive development harness:

```bash
darps play packs/my-game
```

With another configuration file:

```bash
darps play packs/my-game --config configs/local.yaml
```

### Arguments and options

| Parameter | Required | Default | Meaning |
|---|---:|---|---|
| `pack` | Yes | — | Pack directory |
| `--config` | No | `config.yaml` | Runtime provider and behavior configuration |

The harness stands in for a host game. It is useful for prompt iteration,
knowledge checks, attitudes, gates, discoveries, and provider debugging. It
is not a complete game client.

The harness loads the existing local save for the pack from `saves/`, or
creates a fresh state when none exists. Normal calls autosave narrative state.
Host flags exist only in the current harness process unless represented
elsewhere by the host.

### Talk to a character

Use the exact character ID:

```text
@butler What did you hear at ten o'clock?
```

Syntax:

```text
@<character-id> <player message>
```

The harness supplies the addressee directly. DARPS never guesses it from the
message.

### Examine something

```text
x desk search the drawers
x snifter smell the dregs
examine study look around carefully
```

Syntax:

```text
x <target> [message]
examine <target> [message]
```

The target can use the same IDs, names, and aliases accepted by the examination
pipeline. The harness does not provide a production-quality scene inventory;
use the HTTP API to test exact host-controlled locations and accessible items.

### Development-harness commands

| Command | Effect |
|---|---|
| `/flag <name>` | Toggle a host flag between `true` and `false` |
| `/adjust <character> <amount>` | Apply a host-authoritative integer track change |
| `/grant <fact-id>` | Grant a fact directly, bypassing its discovery gates |
| `/canon <text>` | Add host-authored canon when canon building is enabled |
| `/journal` | Print learned facts using their exact journal text |
| `/persona` | Print current session-level persona values |
| `/state` | Print narrative state except conversation transcripts, plus harness flags |
| `/new` | Replace the current pack save with a fresh session and clear harness flags |
| `/quit` | Exit the harness |

Examples:

```text
/flag cabinet_open
/adjust butler 1
/grant torn_letter
/canon The grandfather clock stopped at ten.
/journal
```

`/adjust` uses the pack's default track because the harness command does not
accept a track ID. Use the library or HTTP `/adjust_track` endpoint when the
host needs to select another track or set an absolute value.

`/grant` is intentionally authoritative. It is for simulating a cutscene or
another host system, not for testing whether a normal discovery gate works.

## `darps compile-knowledge`

Build an optional, inspectable routing catalogue for common, ungated
`shared_knowledge`:

```bash
darps compile-knowledge packs/my-game \
  --config config.yaml \
  --level 2
```

### Arguments and options

| Parameter | Required | Default | Meaning |
|---|---:|---|---|
| `pack` | Yes | — | Pack directory |
| `--config` | No | `config.yaml` | Configuration containing the compression provider and model |
| `--output` | No | `<pack>/knowledge-cache.yaml` | Output artifact; relative configured paths resolve from the pack |
| `--level` | No | `2` | Routing representation and semantic word budget |

### Compression levels

| Level | Compiler behavior |
|---:|---|
| `0` | Store full original content; make no model call |
| `1` | One model call; at most 40 words per semantic route |
| `2` | One model call; at most 20 words per semantic route |
| `3` | One model call; at most 12 words per semantic route |

Levels 1–3 make exactly one author-time call over all eligible entries. The
compiler model can be larger than the runtime models:

```yaml
knowledge_cache:
  enabled: true
  path: knowledge-cache.yaml
  compression:
    provider: openai
    model: large-context-model
    temperature: 0.2
    max_tokens: 16000
```

The compiler first validates the pack. It then validates that the model
returned one non-empty, unique, within-budget route for every source ID.
Only a completely valid result atomically replaces the artifact. A failed
call or invalid response leaves the previous file untouched.

At runtime, enable both systems:

```yaml
knowledge_resolver: true
knowledge_cache:
  enabled: true
  path: knowledge-cache.yaml
```

The catalogue affects only resolver prompt size. Selected routes are restored
to exact live YAML before a character briefing or reveal authority is built.
A missing, stale, malformed, or unreadable artifact falls back to the normal
full-corpus resolver.

See [Knowledge](../concepts/knowledge.md#compiling-large-common-knowledge-catalogues)
for the complete model.

## `darps serve`

Run the real integration surface as a localhost HTTP sidecar:

```bash
darps serve packs/my-game
```

Choose a configuration, interface, or port:

```bash
darps serve packs/my-game \
  --config configs/production.yaml \
  --host 127.0.0.1 \
  --port 8080
```

### Arguments and options

| Parameter | Required | Default | Meaning |
|---|---:|---|---|
| `pack` | Yes | — | Pack directory |
| `--config` | No | `config.yaml` | Runtime provider and behavior configuration |
| `--host` | No | `127.0.0.1` | Network interface on which to listen |
| `--port` | No | `8080` | TCP port; `0` requests an available ephemeral port |

The command validates the pack before starting. Validation errors prevent the
server from running.

The sidecar keeps sessions in memory but does not autosave them. The host must
persist and restore state through the session/state API. Confirm startup with:

```bash
curl http://127.0.0.1:8080/health
```

Use localhost unless you deliberately provide an external authentication and
deployment layer. DARPS does not add authentication or TLS itself.

See the [HTTP API reference](../api/http-reference.md) for every route.

## Typical development workflow

```bash
# Create once
darps new packs/my-game

# Repeat while authoring
darps validate packs/my-game
darps play packs/my-game --config config.yaml

# Optional for a large common-knowledge corpus
darps compile-knowledge packs/my-game --config config.yaml --level 2

# Connect the host game
darps serve packs/my-game --config config.yaml
```

Re-run `validate` after content edits. Re-run `compile-knowledge` whenever
contributing common, ungated shared knowledge changes; otherwise the runtime
source hash will reject the stale catalogue and use the full resolver.
