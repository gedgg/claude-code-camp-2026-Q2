# 03 · The Prompt Builder (Python)

Python port of `week1_baseline/ruby/03_prompt_builder`. See
[`docs/plans/python_port/03_prompt_builder`](../../../docs/plans/python_port/03_prompt_builder)
for the full port plan and the decisions behind the differences from Ruby
called out below.

`Config`, `Task`/`Player`, `Tool`, `Message`, `Context`, `Registry` are
unchanged from [`02_the_registry`](../02_the_registry/README.md) — copied
forward verbatim. This step adds `PromptBuilder` and five `backends.*`
classes (payload serialization only — **no HTTP call happens anywhere in
this step**).

## How It Works

```
Context (Python objects)
        ↓
PromptBuilder
        ↓
Backend (Anthropic, OpenAI, Gemini, Ollama, or OllamaCloud)
        ↓
API payload (plain dicts and lists)
        ↓
(a later step POSTs this)
```

## `boukensha.prompt_builder.PromptBuilder`

| Method | Description |
|---|---|
| `to_messages()` | Delegates message serialization to the backend |
| `to_tools()` | Delegates tool serialization to the backend |
| `to_api_payload(max_output_tokens=1024)` | Assembles the complete payload |
| `headers` | The correct headers for the backend (property) |
| `url` | The correct endpoint URL for the backend (property) |

## Backends

Each backend owns its own `MODELS` table (`context_window`, per-million
input/output cost or `None`, `usage_unit`, optional `usage_level`). A
backend refuses to construct with an unknown model, raising
`UnsupportedModelError`. Instances expose `context_window`,
`input_token_cost_per_million`, `output_token_cost_per_million`,
`usage_unit`, `usage_level`, and `estimate_cost(input_tokens=,
output_tokens=)`. Local Ollama models cost `0.0`; Ollama Cloud's usage-based
pricing has no public per-token rate, so `estimate_cost` returns `None`.

| Backend | Endpoint | Auth |
|---|---|---|
| `backends.Anthropic` | `https://api.anthropic.com/v1/messages` | `ANTHROPIC_API_KEY` |
| `backends.Ollama` | `http://localhost:11434/api/chat` | none (local `ollama serve`) |
| `backends.OllamaCloud` | `https://ollama.com/api/chat` | `OLLAMA_API_KEY` |
| `backends.OpenAI` | `https://api.openai.com/v1/chat/completions` | `OPENAI_API_KEY` |
| `backends.Gemini` | `.../v1beta/models/{model}:generateContent` | `GEMINI_API_KEY` |

System-prompt placement, tool-result shape, and message-role naming all
diverge per backend exactly as documented in the Ruby README (Anthropic/
Gemini put the system prompt in a top-level field; Ollama/OllamaCloud/
OpenAI prepend it as a `role: system` message; Gemini renames the
assistant role to `model`) — see the Ruby README for the full per-backend
JSON examples, which apply unchanged here.

## Differences from the Ruby version

- **`model_info` is split into three names because Python can't reuse one
  name for a classmethod and an instance property.** Ruby has
  `self.model_info(model)` (class method: look up any model) and
  `model_info` (instance method: the configured instance's own metadata) —
  same name, different namespaces. Python's port:
  - `Base.models()` — classmethod, the `MODELS` table (raises
    `NotImplementedError` if a subclass hasn't set one, mirroring Ruby's
    `rescue NameError`)
  - `Base.lookup_model(model)` — classmethod, replaces Ruby's class-level
    `model_info(model)`
  - `Base.validate_model(model)` — classmethod, validates or raises
    `UnsupportedModelError`
  - `backend.model_info` — instance property, kept the same name as Ruby's
    instance method since that's the one with no naming conflict
- **`UnsupportedModelError` messages use the unqualified class name**
  (`"Anthropic does not support model..."`), not Ruby's fully-qualified
  `Boukensha::Backends::Anthropic` — `cls.__name__` vs. Ruby's `self.name`
  inside a module nesting Python has no equivalent for.
- **The `PromptBuilder.to_messages()` arity mismatch is ported faithfully,
  not fixed.** `to_messages()` always calls `backend.to_messages(context.
  messages)` — one argument. Anthropic/Gemini's `to_messages(messages)`
  accept that; Ollama/OllamaCloud/OpenAI's `to_messages(system, messages)`
  need two and raise `TypeError` if called this way. Nothing in
  `examples/example.py` calls `builder.to_messages()` directly (only
  `to_api_payload()`, which calls each backend's own `to_messages`
  correctly), so this never surfaces in normal use — it's a real,
  reproducible quirk in the Ruby source, pinned down by a test
  (`test_prompt_builder.py::test_to_messages_arity_mismatch_quirk_ollama_style_backend`)
  rather than silently fixed.
- **`MODELS` tables use plain nested `dict`s with string keys** — Ruby's
  symbol keys (`:context_window`, `:input`, `:tokens`, `:medium`, …) become
  plain Python strings, matching every other symbol→string translation
  already established since `01_struct_skeleton`.
- **Backend selection in `examples/example.py` uses a `match` statement**
  on `provider`, falling through to `boukensha.errors.ConfigError` for an
  unrecognized provider — the same `ArgumentError → ConfigError`
  translation established in `00_config`.

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/{config,tool,message,context,registry}.py`, `tasks/` | Unchanged from `02_the_registry` |
| `src/boukensha/prompt_builder.py` | `PromptBuilder` |
| `src/boukensha/backends/base.py` | `Base`: `MODELS` contract, model validation, cost accessors |
| `src/boukensha/backends/{anthropic,gemini,ollama,ollama_cloud,openai}.py` | Per-backend serialization |
| `prompts/system.md` | Default system prompt (unchanged) |
| `examples/example.py` | Runnable smoke-test — pretty-prints the built API payload |
| `tests/` | pytest coverage of `PromptBuilder` and every backend |

## Run Example

```bash
./week1_baseline/bin/python/03_prompt_builder
```

## Development

```bash
cd week1_baseline/python/03_prompt_builder
uv sync
uv run pytest -v
uv run ruff check src examples tests
```
