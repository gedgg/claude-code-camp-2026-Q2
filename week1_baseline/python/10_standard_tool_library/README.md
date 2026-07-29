# 10 · A Standard Tool Library (Python)

Python port of `week1_baseline/ruby/10_standard_tool_library`. See
[`docs/plans/python_port/10_standard_tool_library`](../../../docs/plans/python_port/10_standard_tool_library)
for the full port plan and the decisions behind the differences from Ruby
called out below.

BOUKENSHA now ships two real, built-in tool modules — `boukensha.tools.
file_system` and `boukensha.tools.shell` — plus `boukensha.tools.mud`
(gated on a separate, not-yet-ported dependency; see below). Instead of
manually registering tools, a real coding harness gives the agent a
standard library of capabilities out of the box.

## What's new

### `boukensha.tools.file_system`

Registers automatically when `working_dir=` is set:

| Tool | Description |
|------|-------------|
| `pwd` | Return the working directory |
| `list_directory` | List files at a path (default `.`) |
| `read_file` | Read a file's contents |
| `write_file` | Write (or create) a file |
| `delete_file` | Delete a file |
| `search_files` | Grep for a regex pattern across the working tree, returns `path:line:content` matches |

All paths are **relative to the working directory**. Absolute paths and
`..` traversals that escape the root are rejected with an error string,
not an exception.

### `boukensha.tools.shell`

Registers automatically when `working_dir=` is set:

| Tool | Description |
|------|-------------|
| `run_command` | Run a shell command inside the working directory |

Commands run with a configurable timeout and an optional allow-list of
permitted executables.

### `boukensha.tools.mud` — real code, but needs a dependency that doesn't exist yet

`Tools.Mud` registers ~24 CircleMUD gameplay tools against a single shared
session. **This module requires a Python port of the separate
`mud_manager` package** (`week0_explore/mud_manager` — a telnet-session
client + CircleMUD command-builder library, ~690 lines of Ruby). That port
**does not exist yet and is explicitly out of scope for this step's
plan** — treated as its own, standalone future porting effort, exactly
mirroring how Ruby keeps `mud_manager` a separate gem rather than folding
it into `boukensha` itself.

Confirmed by actually running `examples/example.py` against this repo's
real, live-configured MUD connection: it fails with `ModuleNotFoundError:
No module named 'mud_manager'` — a clean, expected failure at exactly the
documented dependency boundary, not a bug in this port. `Tools.Mud`'s own
registration/wiring logic is fully implemented and unit-tested against a
**fake** `mud_manager.Session` double (`tests/test_tools/test_mud.py`); it
just can't be exercised for real without that separate package existing.

To keep `import boukensha` working in the (current, common) case where
`mud_manager` isn't installed, `boukensha/tools/mud.py`'s `import
mud_manager` is deferred to inside `register()` rather than sitting at
module top level like Ruby's `require "mud_manager"` does — otherwise
merely importing this package would break wherever `mud_manager` isn't
installed, which today is everywhere.

### New `boukensha.run` / `boukensha.repl` keyword arguments

```python
boukensha.run(
    task="...",
    working_dir="/my/project",
    allowed_commands=["python", "git"],  # None = allow all (default)
    shell_timeout=30,                     # seconds, default 30
)
```

`allowed_commands=None` permits any executable. Pass an explicit list to
lock the agent down:

```python
# Only allow python and git — rm, curl, etc. will be rejected
boukensha.run(task="...", allowed_commands=["python", "git"])
```

`mud=None` (default) auto-registers `Tools.Mud` when `settings.toml` has a
`[mud]` section with both `host` and `username` set; `mud=False` disables
it entirely regardless of config; an explicit `mud={...}` dict always
registers, bypassing config.

### Direct registration

Both file/shell modules can be registered manually if you need finer
control:

```python
from boukensha.tools import file_system, shell

file_system.register(registry, working_dir="/my/project")
shell.register(registry, working_dir="/my/project", timeout=10, allowed_commands=["python"])
```

### `Context.working_dir`

New field — the resolved, absolute working directory (or `None`),
mirroring the same field on the Ruby side.

### REPL banner: validation restored, mud status line added

`09_global_executable` had dropped the REPL banner's API-key/config-dir
validation (a real, flagged regression — see that step's plan/README).
This step **restores it**, confirming the regression really was
temporary, and adds a `mud:` status line that does a **TCP-reachability-
only** probe (not a full login) — probing login here would double-connect
since `Tools.Mud.register` already auto-connects at startup.

### `boukensha_loader.py`: legacy `MUD_NAME` env vars

`MUD_NAME`/`MUD_HOST`/`MUD_PORT`/`MUD_PASSWORD` env vars still work and
take precedence over `settings.toml` when `MUD_NAME` is set (aborts if
`MUD_PASSWORD` is missing).

## Verified live

- `examples/example.py` (the MUD demo) run against this repo's real
  `.boukensha/` config — confirmed it fails exactly at the `mud_manager`
  import boundary, nowhere else.
- A standalone script calling `boukensha.run(working_dir=..., mud=False)`
  against the **real Anthropic API** — the agent correctly listed a
  directory, read a file, and reported its contents back, using the real
  `file_system` tools wired up automatically.
- The same, for `boukensha.tools.shell`'s `run_command` — the agent ran a
  real shell command (via `allowed_commands=["echo"]`) and correctly
  reported its output.

## Differences from the Ruby version

- **Sandboxed path resolution uses `Path.resolve()`, which follows
  symlinks** — Ruby's `File.expand_path` is purely lexical (`.`/`..`
  normalization only, no symlink resolution). For a sandboxed root that is
  itself behind a symlink, or containing a symlink pointing outside the
  root, this could behave differently in principle; in practice this
  repo's tests use `tmp_path`, which resolves consistently for both sides
  of every comparison, so this divergence has no observable effect here —
  flagged for awareness, not treated as a bug.
- **`run_command` always executes via `subprocess.run(..., shell=True)`**,
  the direct equivalent of Ruby's `Open3.capture2e` for command strings
  with shell syntax (multi-word commands like `"ls -la"`). A consequence:
  a nonexistent executable doesn't raise a Python exception (the shell
  itself runs fine) — it surfaces via a nonzero exit code and stderr text,
  same as it would in a real terminal, rather than via the `except
  FileNotFoundError` branch (kept for defensive completeness, but
  effectively unreachable in the `shell=True` path).
- **`Tools.Mud`'s `import mud_manager` is deferred inside `register()`**,
  not at module top level like Ruby's `require "mud_manager"` — a
  necessary adaptation forced by `mud_manager` not existing as an
  installed Python package yet (see above), not a stylistic choice.
- **`session.open?` becomes the `is_open` property**, not a method call —
  matches this port's established `?`-suffix → plain-attribute convention.

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/tools/file_system.py` | `register(registry, working_dir=)`: six sandboxed file tools |
| `src/boukensha/tools/shell.py` | `register(registry, working_dir=, timeout=30, allowed_commands=None)`: `run_command` |
| `src/boukensha/tools/mud.py` | `register(registry, host=, port=, *, name, password)` — needs the separate `mud_manager` package |
| `src/boukensha/context.py` | +`working_dir` |
| `src/boukensha/repl.py` | Banner validation restored; +`mud=` kwarg, `_mud_status_string`/`_probe_mud` |
| `src/boukensha/__init__.py` | `run()`/`repl()` gain `working_dir`/`allowed_commands`/`shell_timeout`/`mud`; `_mud_opts_from_config` |
| `src/boukensha_loader.py` | +`MUD_NAME`/etc legacy env-var handling |
| `examples/example.py` | Live MUD demo (`working_dir=False`) — needs a real `mud_manager` port + reachable server to actually run |
| `tests/test_tools/` | `test_file_system.py`, `test_shell.py` (real I/O, no mocks), `test_mud.py` (fake `mud_manager.Session`, no real socket) |

## Run Example

```bash
./week1_baseline/bin/python/10_standard_tool_library
```

Requires a real, reachable CircleMUD server **and** a Python port of
`mud_manager` (not yet built) to actually run to completion — see the
"real code, but needs a dependency" note above.

## Development

```bash
cd week1_baseline/python/10_standard_tool_library
uv sync
uv run pytest -v
uv run ruff check src examples tests
```
