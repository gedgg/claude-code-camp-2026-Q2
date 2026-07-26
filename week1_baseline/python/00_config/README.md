# 00 · Configuration (Python)

Python port of `week1_baseline/ruby/00_config`. See
[`docs/plans/python_port/00_config`](../../../docs/plans/python_port/00_config)
for the full port plan and the decisions behind the differences from Ruby
called out below.

We manage all configuration from an external directory, `~/.boukensha/` by
default, via a dedicated `boukensha.config.Config` class. Configuration is
organised by **task** — a role in the agentic loop bound to its own LLM.
week1_baseline only drives a single `player` task (the main loop); a more
advanced loop will assign different LLMs to different tasks. A task is either
a "single-task" or a "multi-task" — the latter being a full agent.

## Differences from the Ruby version

- **Settings format is TOML, not YAML** (`settings.toml`, not
  `settings.yaml`). Python's standard library ships a TOML reader
  (`tomllib`, 3.11+) but no YAML parser, so TOML lets this port avoid an
  external parsing dependency the way the Ruby side does with YAML's stdlib
  `yaml`.
- Only external dependency is `python-dotenv` (mirrors Ruby's one deliberate
  exception, the `dotenv` gem).
- `Boukensha::Tasks::Base`/`Player` → `boukensha.tasks.base.Task` /
  `boukensha.tasks.player.Player`, kept as classmethod-only, never
  instantiated, for structural parity with the Ruby class-method design.
- Ruby's `ArgumentError` on missing `provider`/`model` → Python's
  `boukensha.errors.ConfigError`.

## Design Considerations

Use the standard library as much as possible avoiding external dependencies.
`python-dotenv` is the one exception, to load `.env` files.

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/config.py` | `Config` class |
| `src/boukensha/errors.py` | `ConfigError` |
| `src/boukensha/tasks/base.py` | abstract `Task` (provider/model + prompt resolution) |
| `src/boukensha/tasks/player.py` | concrete `Player` (the main loop) |
| `src/boukensha/__init__.py` | top-level package exports |
| `prompts/system.md` | default system prompt shipped with the library |
| `examples/example.py` | runnable smoke-test |
| `tests/` | pytest coverage of `Config` and `Task` behaviour |

---

## Config directory resolution

The class looks for a `.boukensha/` directory in this order:

1. **`BOUKENSHA_DIR` env var** — set this to point at any directory you like.
2. **`~/.boukensha`** — the default location for a real install.

## Config directory structure

```
.boukensha/
  .env                 # stores credentials eg. LLMs APIs (never committed to repo)
  settings.toml        # all non-secret settings
  prompts/
    <task>/
      system.md        # per-task override for the default system prompt (optional)
```

---

## Tasks

`boukensha.tasks.base.Task` is an abstract stateless class. All behaviour is
expressed as classmethods that accept a `settings` dict — no instances are
created. Concrete subclasses define `.task_name()`. For now only `Player`
exists; future steps add per-turn ceilings (`max_iterations`,
`max_turn_tokens`, `max_output_tokens`, `compaction_threshold`) — these are
**not** read yet.

`Config.tasks()` returns the raw dict from `settings.toml` under `[tasks]`.
Pass a name to look up a specific task's settings dict, then pass it to the
stateless class:

```python
Player.provider(config.tasks("player"))
Player.system_prompt(
    config.tasks("player"),
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=PROMPTS_DIR,
)
```

## System prompt resolution

Per task, `Player.system_prompt` is resolved in this order:

1. **`.boukensha/prompts/<task>/system.md`** — used when the task's
   `prompt_override.system` is `true` and the file exists.
2. **`prompts/system.md`** — the default system prompt shipped with the
   library.

## Configuration Schema

The following properties so far:
- `tasks`: a table of task name → task config (provider, model,
  prompt_override).
- `tasks.<name>.prompt_override.system`: when `true`, the task's
  `.boukensha/prompts/<name>/system.md` overrides the default system prompt.
- `mud`: MUD connection information for the main player.

```toml
[tasks.player]
provider = "anthropic"        # provider name (string)
model = "claude-haiku-4-5"

[tasks.player.prompt_override]
system = true

[mud]
host = "localhost"
port = 4000
username = "dummy"
password = "helloworld"
```

## Run Example

```bash
./week1_baseline/bin/python/00_config
```

Expected output (values from your `.boukensha/`):

```
=== Boukensha Step 0: Configuration (Python) ===

Config dir:     /home/andrew/Sites/Claude-Code-Camp/.boukensha
Tasks:          player

-- player task --
Provider:       anthropic
Model:          claude-haiku-4-5
Prompt override?True
System prompt:  You are a MUD player assistant. Use the tools available to y...

MUD host:       localhost:4000
MUD user:       dummy

API key set?    True

#<Boukensha::Config dir=/home/andrew/Sites/Claude-Code-Camp/.boukensha tasks=player>
```

## Development

```bash
cd week1_baseline/python/00_config
uv sync
uv run pytest -v
uv run ruff check src
```
