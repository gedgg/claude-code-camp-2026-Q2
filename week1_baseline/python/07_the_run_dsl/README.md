# 07 · The `boukensha.run` DSL (Python)

Python port of `week1_baseline/ruby/07_the_run_dsl`. See
[`docs/plans/python_port/07_the_run_dsl`](../../../docs/plans/python_port/07_the_run_dsl)
for the full port plan and the decisions behind the differences from Ruby
called out below.

Every previous step required manually creating and wiring together a
`Context`, `Registry`, backend, `PromptBuilder`, `Client`, `Logger`, and
`Agent`. This step hides all of that behind one function call:
`boukensha.run`.

## `boukensha.run`

```python
import boukensha

result = boukensha.run(
    task="Read src/boukensha/__init__.py",
    register=lambda dsl: dsl.tool(
        "read_file",
        description="Read a file from disk",
        parameters={"path": {"type": "string", "description": "File path"}},
        block=lambda *, path: Path(path).read_text(),
    ),
)
```

| Option | Default | Description |
|---|---|---|
| `task` | *(required)* | The user message handed to the agent |
| `system` | the player task's configured prompt | System prompt |
| `model` | the player task's configured model | Model name |
| `backend` | the player task's configured provider | `"anthropic"`, `"openai"`, `"gemini"`, `"ollama"`, or `"ollama_cloud"` |
| `api_key` | the matching `*_API_KEY` env var | API key (not needed for `"ollama"`) |
| `ollama_host` | `"http://localhost:11434"` | Ollama base URL |
| `log` | `None` | Optional JSONL path override; defaults to `.boukensha/sessions/<session-id>.jsonl` |
| `max_output_tokens` | the task's configured value (1024) | Per-reply output cap |
| `register` | `None` | Callable receiving a `RunDSL` instance, for registering tools |

## `boukensha.run_dsl.RunDSL`

A tiny host object passed to `register`. Exposes exactly one method,
`tool`, keeping the surface intentionally small.

## Differences from the Ruby version

- **Ruby's `instance_eval`-based DSL block has no Python equivalent — this
  is the one unavoidable call-site divergence in this whole port.** Ruby's
  `Boukensha.run(task: "...") { tool ... }` works because `instance_eval`
  temporarily rebinds `self` inside the block so bare `tool(...)` calls
  resolve against a `RunDSL` instance. Python has no mechanism for
  rebinding what a bare-name call resolves against inside an
  already-defined function, so the Python port instead accepts `register:
  Callable[[RunDSL], None] | None = None` and calls it as `register(dsl)`
  — callers write `boukensha.run(task="...", register=lambda dsl:
  dsl.tool(...))`, explicitly naming `dsl` where Ruby's block gets it for
  free as implicit `self`.
- **`run()` is a plain module-level function**, not a method on some
  `Boukensha` class — matching Ruby's `Boukensha.run` being a module
  function, not an instance method.
- **`case backend ... else raise ArgumentError` becomes a chain of `if`s
  ending in `raise ConfigError`,** consistent with the `ArgumentError →
  ConfigError` translation convention established since `00_config`.
- **`x ||= default` uses `is None` throughout, not bare Python
  truthiness,** matching Ruby's `nil`/`false`-only falsy semantics — most
  visibly for `max_output_tokens`, where a `0` passed explicitly must be
  preserved, not silently replaced by the task's configured default.
- **`mud_host`/etc. and `LoopError` reappear this step** — both were
  removed in `06_the_logger` (temporarily, matching Ruby's own history) and
  are restored here, still unused by anything.
- **`Logger` gains `turn(n=)`** (writes a `phase: "turn"` event — not yet
  called by anything in this step; used starting `08_the_repl_loop`) and
  `subscribe(callback)` (a registered callback receives every event dict,
  in addition to the file write).

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/{tool,message,context,registry,prompt_builder,client,agent,backends}.py`, `tasks/` | Unchanged from `06_the_logger` |
| `src/boukensha/config.py` | `mud_*` accessors restored |
| `src/boukensha/errors.py` | `LoopError` restored |
| `src/boukensha/logger.py` | +`turn(n)`, +`subscribe(callback)` |
| `src/boukensha/run_dsl.py` | `RunDSL` |
| `src/boukensha/__init__.py` | +`run()` |
| `examples/example.py` | `boukensha.run(task=..., register=...)` |
| `tests/test_run.py` | New — `boukensha.run()` with the backend/client layer faked, no real network calls |
| `tests/test_run_dsl.py` | New |

## Run Example

```bash
./week1_baseline/bin/python/07_the_run_dsl
```

## Development

```bash
cd week1_baseline/python/07_the_run_dsl
uv sync
uv run pytest -v
uv run ruff check src examples tests
```
