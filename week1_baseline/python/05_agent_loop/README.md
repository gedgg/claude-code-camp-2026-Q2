# 05 · The Agent Loop (Python)

Python port of `week1_baseline/ruby/05_agent_loop`. See
[`docs/plans/python_port/05_agent_loop`](../../../docs/plans/python_port/05_agent_loop)
for the full port plan and the decisions behind the differences from Ruby
called out below.

`Registry`, `Tool`, `Message`, `Context`, `Config` are unchanged from
[`04_api_client`](../04_api_client/README.md). This step adds `Agent` (the
tool-calling loop) and a normalized `{"stop_reason", "content"}` response
shape every backend now produces via `parse_response`. This is where
BOUKENSHA becomes an actual tool-calling agent rather than a single
request/response demo.

## How It Works

```
Agent.run()
  ├─ call the model (Client.call)
  ├─ builder.parse_response(response) → {"stop_reason", "content"}
  ├─ stop_reason == "tool_use"?
  │    ├─ yes → dispatch every tool_use block via Registry, append
  │    │        tool_result messages, loop again
  │    └─ no  → extract text from content blocks, return it
  └─ iteration ceiling reached? → one tools-disabled "wrap-up" call, return that instead
```

## `boukensha.agent.Agent`

`Agent(context=, registry=, builder=, client=, task_settings=None,
max_iterations=None, max_output_tokens=None)` — `run()` executes the loop
to completion and returns the final text.

- **The normalized response shape** every `parse_response` produces:
  `{"stop_reason": "tool_use" | "end_turn", "content": [...]}`, where each
  content block is `{"type": "text", "text": ...}` or `{"type": "tool_use",
  "id": ..., "name": ..., "input": {...}}`. `Agent` only ever inspects this
  shape, never a raw provider response.
- **Tool-call IDs aren't universal.** Anthropic assigns a real `id` per
  call, echoed back in the tool result. Ollama, Ollama Cloud, and Gemini
  don't — those backends reuse the tool's `name` as its `id`, matching by
  name on replay. OpenAI also assigns a real `id`.
- **The assistant message is stored before its tool results**, in API
  order. `Message.content` is polymorphic: a plain string for ordinary
  turns, or a list of normalized content blocks for a turn that included
  tool calls — every backend's `_assistant_message`/`_assistant_parts` (or
  Anthropic's direct pass-through) handles both shapes on replay.
- **The loop terminates on `stop_reason == "end_turn"`.** The model is the
  only thing that ends a turn normally; the agent never decides
  unilaterally to stop except via the iteration ceiling.
- **The iteration ceiling is a trigger threshold, not a hard cap.** Once
  reached, the loop makes exactly one additional wind-down call — tools
  disabled, a short injected user directive, capped output — instead of
  raising. That call runs outside the counted loop and falls back to a
  deterministic message if the text comes back empty or the call itself
  raises `ApiError`.
- **A ceiling of `0` disables it entirely.**
- **Multiple tool calls in one response are all dispatched before the next
  API round-trip.**

## Differences from the Ruby version

- **`Agent`'s Ruby `private` methods become leading-underscore instance
  methods** (`_resolve_max_iterations`, `_call_opts`, `_wrap_up`, etc.) — a
  direct translation, no behavioural change.
- **`Agent._call_opts` uses an explicit `is not None` check, not Python
  truthiness,** to mirror Ruby's `@max_output_tokens ? ... : {}`. Ruby only
  treats `nil`/`false` as falsy — `0` is truthy in Ruby — so a bare `if
  self._max_output_tokens:` in Python would incorrectly treat a
  (nonsensical but possible) `0` as "not set."
- **`_resolve_max_iterations`'s Ruby `.to_i` becomes `int(explicit)`** —
  both coerce whatever was passed; Python's `int()` raises `ValueError` on
  a non-numeric string, which is an accepted stricter behaviour (Ruby's
  `.to_i` would silently return `0` instead — but this path is only hit
  when a caller explicitly passes a non-`None`, non-numeric value, an edge
  case with no real call site in this codebase).
- **`_integer_setting`'s Ruby `Integer(value)`** (strict — raises on
  non-integer-looking strings) becomes Python's plain `int(value)`, which
  already has the same strictness — no extra validation needed.
- **OpenAI's tool-call `arguments` are a JSON-encoded string on the wire**
  (`json.dumps`/`json.loads`), unlike every other backend's dict — a real,
  backend-specific API contract difference, ported faithfully per-backend.
- **Two independent sources of default iteration/token limits exist and
  are not unified:** `Agent.MAX_ITERATIONS = 25` (used when no
  `task_settings` is given, or the task doesn't define `max_iterations`)
  and `Task.DEFAULT_MAX_ITERATIONS = 25` (used inside `Task.max_iterations`
  when the setting itself is absent). They agree numerically but are
  genuinely separate constants in two separate classes, matching Ruby.
- **`LoopError` is ported but unused** — defined in `errors.py` for
  structural parity; nothing in this step (or the Ruby source) raises it.

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/{config,tool,message,context,registry}.py` | Unchanged from `04_api_client` |
| `src/boukensha/tasks/base.py` | `Task`: +`max_iterations`/`max_output_tokens`/`DEFAULT_*` constants |
| `src/boukensha/errors.py` | +`LoopError` (unused) |
| `src/boukensha/prompt_builder.py` | +`parse_response`; `to_api_payload` gains a `tools=` override passthrough |
| `src/boukensha/client.py` | `call()` gains a `tools=` kwarg |
| `src/boukensha/backends/*.py` | +`parse_response`; `to_payload` accepts a `tools=` override; Ollama/OllamaCloud/OpenAI gain `_assistant_message`, Gemini gains `_assistant_parts` |
| `src/boukensha/agent.py` | `Agent` |
| `examples/example.py` | Full run: config/context/registry/backend/builder/client/agent, `read_file`+`list_directory` tools, real network calls |
| `tests/test_agent.py` | Fake registry/builder/client doubles — no real network calls |

## Run Example

```bash
./week1_baseline/bin/python/05_agent_loop
```

This makes real network calls to the configured provider in a loop until
the model stops calling tools.

## Development

```bash
cd week1_baseline/python/05_agent_loop
uv sync
uv run pytest -v
uv run ruff check src examples tests
```
