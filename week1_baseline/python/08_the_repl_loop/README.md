# 08 · The REPL Loop (Python)

Python port of `week1_baseline/ruby/08_the_repl_loop`. See
[`docs/plans/python_port/08_the_repl_loop`](../../../docs/plans/python_port/08_the_repl_loop)
for the full port plan and the decisions behind the differences from Ruby
called out below.

| | Step 6 | Step 7 |
|---|---|---|
| Entry point | `boukensha.run(task="…")` | `boukensha.repl()` |
| Turns | one | many |
| History | discarded | accumulates across turns |
| User interaction | none | stdin prompt |

## New primitives

### `boukensha.repl.Repl`

The interactive session loop. Built-in commands:

| Command | Effect |
|---|---|
| `/quiet` | Suppress logging output |
| `/loud` | Re-enable logging output |
| `/clear` | Wipe conversation history (tools stay registered) |
| `/help` | Print the command list |
| `/exit` / `/quit` | Leave the REPL |
| Ctrl-D | EOF — leave the REPL |
| Ctrl-C | Interrupt — leave the REPL gracefully |

### `boukensha.repl`

Same signature as `boukensha.run`, minus `task`. Register tools via
`register=`; then the REPL loop takes over.

```python
boukensha.repl(
    model="claude-haiku-4-5",
    register=lambda dsl: dsl.tool(
        "read_file",
        description="Read a file from disk",
        parameters={"path": {"type": "string", "description": "File path"}},
        block=lambda *, path: Path(path).read_text(),
    ),
)
```

## Changes from step 07

### `Context.clear_messages()`

Wipes `messages` while keeping tools registered. Used by the REPL `/clear`
command.

### `Agent.run` — persists the final reply

Before this step, the agent returned the final text without adding it to
the context. That was fine for one-shot runs (context is thrown away
anyway), but a REPL needs the full transcript so subsequent turns see the
prior exchange — on *both* the normal `end_turn` path and both branches of
`wrap_up` (success and the `ApiError` fallback).

```python
# 06_the_logger / 07_the_run_dsl — final text returned but NOT in context
return text

# 08_the_repl_loop — final text added to context, then returned
self._context.add_message("assistant", text)
return text
```

### `Logger.turn(n=)`

Used at the start of each REPL turn (not yet echoed to stdout by anything
in this step — the logger only ever writes to the JSONL file).

### `Config._resolve_dir` gains a cwd tier

Resolution order is now: `BOUKENSHA_DIR` env var → `.boukensha/` in the
current working directory (if it exists) → `~/.boukensha` default.

### `Client` gains a friendlier 401 message

A `401` response now raises `ApiError("authentication failed (401) — check
your API key")` instead of the generic attempt-count message — still not
retried (401 isn't in the retryable-status set), just a clearer message.

## Differences from the Ruby version

- **The stdin read loop uses `input()` + `except EOFError`,** the direct
  Python equivalent of Ruby's `$stdin.gets` returning `nil` at EOF vs. a
  blank string for an empty line — `input()` raises `EOFError` at true
  EOF, letting the loop distinguish "Ctrl-D" (silent exit, no "Goodbye.")
  from "blank line" (skipped, not counted as a turn) unambiguously.
- **`rescue Interrupt` becomes `except KeyboardInterrupt`,** caught one
  level up — inside `boukensha.repl()`, not inside `Repl.start()` — same
  as Ruby's structure (`Boukensha.repl`'s own `rescue Interrupt`, not
  `Repl#start`'s).
- **`Repl`'s Ruby `private` methods become leading-underscore instance
  methods** (`_banner`, `_run_turn`) — no behavioural change.

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/{tool,message,registry,prompt_builder,client,backends,run_dsl}.py`, `tasks/` | Mostly unchanged from `07_the_run_dsl` (`client.py` gains the 401 case) |
| `src/boukensha/context.py` | +`clear_messages()` |
| `src/boukensha/config.py` | `_resolve_dir` gains the cwd-`.boukensha` tier |
| `src/boukensha/agent.py` | Persists the final reply to context on `end_turn` and both `wrap_up` branches |
| `src/boukensha/logger.py` | +`turn(n)` |
| `src/boukensha/version.py` | New: `VERSION = "0.8.0"` |
| `src/boukensha/repl.py` | `Repl` |
| `src/boukensha/__init__.py` | +`repl()` |
| `examples/example.py` | `boukensha.repl(register=...)` |
| `tests/test_repl.py` | New — stdin/stdout faked, no real network |

## Run Example

```bash
./week1_baseline/bin/python/08_the_repl_loop
```

## Development

```bash
cd week1_baseline/python/08_the_repl_loop
uv sync
uv run pytest -v
uv run ruff check src examples tests
```
