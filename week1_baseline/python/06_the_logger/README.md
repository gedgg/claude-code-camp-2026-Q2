# 06 · The Logger (Python)

Python port of `week1_baseline/ruby/06_the_logger`. See
[`docs/plans/python_port/06_the_logger`](../../../docs/plans/python_port/06_the_logger)
for the full port plan and the decisions behind the differences from Ruby
called out below.

`Registry`, `Tool`, `Message`, `Context`, `Config` (minus `mud_*`, see
below), all five backends, `Client`, `PromptBuilder` are carried forward
from [`05_agent_loop`](../05_agent_loop/README.md). This step adds
`boukensha.logger.Logger` — structured JSONL session logs — and
instruments `Agent` throughout. `boukensha.Logger` is a file logger, not
user-facing display output.

## Session Logs

Each `Logger` instance creates a session id and writes one log file for
that session:

```text
.boukensha/sessions/<session-id>.jsonl
```

Every line is a complete JSON object with `session_id`, `at`, and `phase`
fields, plus phase-specific data.

```json
{"phase": "session_start", "session_id": "20260528T143011Z-a1b2c3d4", "at": "..."}
{"phase": "iteration", "n": 1, "session_id": "20260528T143011Z-a1b2c3d4", "at": "..."}
```

Model response lines include the active task, provider, model, normalized
token counts, and estimated USD cost when the backend has token pricing
data.

## `boukensha.logger.Logger`

| Method | Phase | Logs |
|---|---|---|
| `iteration(n=, max=)` | `iteration` | loop counter |
| `prompt(messages=, tools=)` | `prompt` | messages, tools |
| `tool_call(name=, args=)` | `tool_call` | tool name and arguments |
| `tool_result(name=, result=, ok=, error=)` | `tool_result` | tool result |
| `response(text=, usage=, stop_reason=, task=, backend=)` | `response` | response text, token usage, task/provider/model, estimated cost |
| `raw(data=)` | `raw` | raw provider response — only written when `boukensha.debug()` was called |
| `subscribe(callback)` | — | registers a callback invoked with every event dict, in addition to the file write |

```python
logger = Logger()
agent = Agent(context=ctx, registry=registry, builder=builder, client=client, logger=logger)
```

Override the destination:

```python
Logger(session_id="manual-session")
Logger(dir="/tmp/boukensha-sessions")
```

## Module-level state (`boukensha.quiet()`/`.loud()`/`.debug()`/`.get_config()`)

```python
import boukensha

boukensha.debug()       # include raw provider responses in the log
boukensha.quiet()        # (currently has no stdout effect — reserved for a later step)
boukensha.get_config()   # memoized Config() — same instance across the whole process
```

## Behavioural notes

- **Tool-dispatch errors are now caught, not propagated.** `Agent.
  _handle_tool_calls` wraps `registry.dispatch(name, args)` in a `try/
  except Exception`, turning any exception into the string `"ERROR:
  <ExceptionType>: <message>"` — sent back to the model as the
  `tool_result` content instead of crashing the loop, and logged via
  `tool_result(ok=False, error=...)`.
- **`Logger.response`'s metadata is computed from `builder.backend`,**
  which is why `PromptBuilder.backend` is now a public attribute (it
  wasn't externally readable before this step).

## Differences from the Ruby version

- **Module-level `quiet!`/`loud!`/`quiet?`/`debug!`/`debug?`/`config`
  become plain module functions** (`boukensha.quiet()`, `.loud()`, `.
  is_quiet()`, `.debug()`, `.is_debug()`, `.get_config()`) backed by
  module-level globals — the direct translation of Ruby module-level
  instance variables, since Python has no equivalent "module as an object
  with its own state" idiom beyond module globals.
- **`Logger` avoids a circular import with `__init__.py`** (which needs
  `from .logger import Logger` for re-export, while `logger.py` needs
  `is_debug()`/`get_config()` from `__init__.py`) by doing `import
  boukensha as _boukensha` *inside* the two methods that need it (`raw`,
  `_default_dir`), not at module top-level — deferring the lookup until
  after `boukensha/__init__.py` has finished executing.
- **`Agent`'s `logger: Logger.new` Ruby default (evaluated fresh per call)**
  becomes `logger: Logger | None = None` with `self._logger = logger if
  logger is not None else Logger()` in the constructor body — not `logger:
  Logger = Logger()` in the signature, which would share one `Logger`
  instance (and one open file handle) across every `Agent` that omits it.
- **CamelCase→snake_case for the logged `provider` field** uses
  `re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()` on `type(backend).
  __name__`, the direct equivalent of Ruby's `.gsub(...).downcase` on the
  unqualified class name (Python has no module-qualified class-name string
  to strip a namespace prefix from, unlike Ruby's `Boukensha::Backends::`).
- **`mud_host`/`mud_port`/`mud_username`/`mud_password` are removed from
  `Config` in this step** (temporarily — matching Ruby's own history,
  where this exact step deletes them as genuinely-dead code and
  `07_the_run_dsl` re-adds them). **`LoopError` is likewise removed from
  `errors.py`** this step, also re-added in `07_the_run_dsl`.

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/{tool,message,context,registry,client,prompt_builder}.py`, `backends/`, `tasks/` | Carried forward from `05_agent_loop` (`prompt_builder.py`'s `backend` attribute is now public) |
| `src/boukensha/config.py` | `mud_*` accessors removed this step |
| `src/boukensha/errors.py` | `LoopError` removed this step |
| `src/boukensha/logger.py` | `Logger` |
| `src/boukensha/agent.py` | `Agent`: +`logger` kwarg, full instrumentation, tool-dispatch error handling |
| `src/boukensha/__init__.py` | +module-level `quiet`/`loud`/`is_quiet`/`debug`/`is_debug`/`get_config` |
| `examples/example.py` | Builds a `Logger()`, passes it into `Agent` |
| `tests/test_logger.py` | New |
| `tests/test_agent.py` | Extended: logger instrumentation sequence, tool-dispatch-error path |

## Run Example

```bash
./week1_baseline/bin/python/06_the_logger
```

## Development

```bash
cd week1_baseline/python/06_the_logger
uv sync
uv run pytest -v
uv run ruff check src examples tests
```
