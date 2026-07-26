# 02 · The Registry (Python)

Python port of `week1_baseline/ruby/02_the_registry`. See
[`docs/plans/python_port/02_the_registry`](../../../docs/plans/python_port/02_the_registry)
for the full port plan and the decisions behind the differences from Ruby
called out below.

The Tool Registry is how BOUKENSHA manages what capabilities the agent can
use. It has two jobs:
1. storing tools
2. dispatching tools when asked

`Config`, `Task`/`Player`, `Tool`, `Message`, and `Context` are unchanged
from [`01_struct_skeleton`](../01_struct_skeleton/README.md) — this step
copies them forward verbatim and adds `Registry` and `UnknownToolError`
below.

## How It Works

The agent NEVER calls a tool directly. It emits a structured request (name
and args) and the Registry looks up the tool and runs it.

```
Agent:    "Hey registry call move with direction='north'"
Registry: "looking up 'move' in the tool table"
Registry: "Found it now calling the block with the provided args"
Registry: "Here's the result"
Agent:    "Thanks buddy"
Registry: "Thats why you pay me the big tokes"
```

## `boukensha.registry.Registry`

| Method | Description |
|---|---|
| `tool(name, *, description, parameters=None, block=None)` | Registers a new tool on the context, returns the `Tool` |
| `dispatch(name, args=None)` | Looks up a tool by name and calls it with the provided args |

## `boukensha.errors.UnknownToolError`

Raised when `dispatch` is called with a name that has no registered tool. A
harness needs explicit error boundaries — an unrecognised tool name should
never silently fail.

**Example:**
```
UnknownToolError: No tool registered as 'flee'
```

## Differences from the Ruby version

- **No trailing-block syntax.** Ruby's `tool(...) do |direction:| ... end`
  captures a trailing block implicitly. Python has no equivalent, so `tool`
  takes a plain `block: Callable` keyword argument instead — passed as a
  `lambda` at the call site, the same way `01_struct_skeleton`'s
  `examples/example.py` already passes callables to `Tool.block`.
- **No symbol/string key translation in `dispatch`.** Ruby's `dispatch` does
  `args.transform_keys(&:to_sym)` before calling the block, because the API
  hands back string-keyed JSON but Ruby keyword-arg blocks expect symbol
  keys — the Ruby README calls this out as a deliberate "gotcha" left
  visible for learning. Python dict keys are always `str`, and `**args`
  unpacks them straight into keyword arguments, so this translation step
  simply doesn't exist here — nothing was ported, because there's nothing
  to port.
- `Boukensha::UnknownToolError` → `boukensha.errors.UnknownToolError`, a
  straight 1:1 port (Ruby already gives this one a specific name, unlike
  `ArgumentError → ConfigError` back in `00_config`).

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/config.py` | `Config` class (unchanged from `01_struct_skeleton`) |
| `src/boukensha/errors.py` | `ConfigError` + new `UnknownToolError` |
| `src/boukensha/tasks/{base,player}.py` | `Task`/`Player` (unchanged) |
| `src/boukensha/tool.py` | `Tool` dataclass (unchanged) |
| `src/boukensha/message.py` | `Message` dataclass (unchanged) |
| `src/boukensha/context.py` | `Context` class (unchanged) |
| `src/boukensha/registry.py` | `Registry`: `tool`/`dispatch` |
| `src/boukensha/__init__.py` | top-level package exports |
| `prompts/system.md` | default system prompt shipped with the library |
| `examples/example.py` | runnable smoke-test |
| `tests/` | pytest coverage of `Config`, `Task`, `Tool`, `Message`, `Context`, `Registry` |

## Run Example

```bash
./week1_baseline/bin/python/02_the_registry
```

Expected output (values from your `.boukensha/`):

```
=== BOUKENSHA Step 2: Tool Registry ===

Config:  #<Boukensha::Config dir=/home/andrew/Sites/Claude-Code-Camp/.boukensha tasks=player>
Context: #<Context task=player turns=0 tools=2>
Tools:
  #<Tool name=move description=Move the player in a direction (north, so params=['direction']>
  #<Tool name=shout description=Shout a message so everyone in the zone c params=['message']>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

## Development

```bash
cd week1_baseline/python/02_the_registry
uv sync
uv run pytest -v
uv run ruff check src
```
