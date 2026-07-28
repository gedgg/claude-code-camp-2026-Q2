# Ruby → Python Port: Running Context

This file is the ongoing log for the Ruby → Python port of the `boukensha`
agentic loop. It is updated every time a step is planned or ported, so a
future session (or a future you) can pick up mid-port without re-deriving
what's already decided. One plan file per numbered baseline step lives
alongside this one (`00_config`, `01_*`, …, as they're ported); this file is
the index and the decision record across all of them.

Status legend: ✅ done · 🚧 in progress · ⬜ not started

## Steps

| Step | Ruby source | Python target | Status |
|------|-------------|----------------|--------|
| `00_config` | `week1_baseline/ruby/00_config` | `week1_baseline/python/00_config` | ✅ done |
| `01_struct_skeleton` | `week1_baseline/ruby/01_struct_skeleton` | `week1_baseline/python/01_struct_skeleton` | ✅ done |
| `02_the_registry` | `week1_baseline/ruby/02_the_registry` | `week1_baseline/python/02_the_registry` | ✅ done |
| `03_prompt_builder` | `week1_baseline/ruby/03_prompt_builder` | `week1_baseline/python/03_prompt_builder` | ⬜ planned |
| `04_api_client` | `week1_baseline/ruby/04_api_client` | `week1_baseline/python/04_api_client` | ⬜ planned |
| `05_agent_loop` | `week1_baseline/ruby/05_agent_loop` | `week1_baseline/python/05_agent_loop` | ⬜ planned |
| `06_the_logger` | `week1_baseline/ruby/06_the_logger` | `week1_baseline/python/06_the_logger` | ⬜ planned |
| `07_the_run_dsl` | `week1_baseline/ruby/07_the_run_dsl` | `week1_baseline/python/07_the_run_dsl` | ⬜ planned |
| `08_the_repl_loop` | `week1_baseline/ruby/08_the_repl_loop` | `week1_baseline/python/08_the_repl_loop` | ⬜ planned |
| `09_global_executable` | `week1_baseline/ruby/09_global_executable` | `week1_baseline/python/09_global_executable` | ⬜ planned |
| `10_standard_tool_library` | `week1_baseline/ruby/10_standard_tool_library` | `week1_baseline/python/10_standard_tool_library` | ⬜ planned |

Nothing has been committed to git yet — everything below is working-tree
state as of 2026-07-26. Plans for `03`–`05` were written 2026-07-27, ahead
of implementation, so a future porting session can start straight from
them. Plans for `06`–`10` were written 2026-07-28, completing the plan
coverage for every numbered Ruby step that exists in `week1_baseline/ruby/`
as of this writing — none of `03`–`10` are implemented yet.

---

## 06_the_logger / 07_the_run_dsl / 08_the_repl_loop / 09_global_executable / 10_standard_tool_library — planned, not yet ported (2026-07-28)

Plans: [`06_the_logger`](06_the_logger), [`07_the_run_dsl`](07_the_run_dsl),
[`08_the_repl_loop`](08_the_repl_loop),
[`09_global_executable`](09_global_executable),
[`10_standard_tool_library`](10_standard_tool_library)

Written the same way as `03`–`05`: examining the Ruby sources directly
(`diff`-ing each step against its predecessor) since none of these five
exist under `week1_baseline/python/` yet, and none of `03`–`05` are
implemented yet either — so this chain of five plans is written entirely
against Ruby source, with each plan's "Reference files" pointing at the
*previous plan document* (not real Python code) for the parts that don't
change. If `03`–`05` land with different decisions than their plans
currently describe, the "unchanged copy" assumptions in `06`–`10` should
be re-checked the same way `03`'s own loose-thread note already warns.

Notable findings surfaced while planning (full detail in each plan file):

- **`06_the_logger`** introduces `Boukensha::Logger` (structured JSONL
  session logs) and instruments `Agent` throughout. Found a real, lasting
  behavioural change (not a quirk): tool-dispatch errors are now caught
  and turned into an `"ERROR: ..."` string `tool_result` instead of
  crashing the loop. Also found a **short-lived Ruby-side deletion**:
  `Config#mud_host`/etc. and `errors.rb`'s `LoopError` are both removed in
  this step and **reappear in `07_the_run_dsl`** — recommended porting the
  removal faithfully here and re-adding both in the next step, exactly
  mirroring Ruby's own history rather than leaving them in "just in case."
  Flagged a real circular-import design problem for Python's module-level
  `quiet!`/`debug!`/`config` state living in `__init__.py` while
  `logger.py` needs to read it — recommended a deferred `import boukensha`
  inside `logger.py`'s method bodies.
- **`07_the_run_dsl`** introduces the `Boukensha.run` one-call entry point
  and `RunDSL`. Found real README inaccuracies: the docs describe only two
  backends and two nonexistent options (`token_budget:`, `max_tokens:`)
  that don't exist in the real five-backend, `max_output_tokens:`-only
  signature — recommended the Python README describe the real signature,
  not the Ruby README's stale one. The bigger design problem: Ruby's
  `instance_eval`-based DSL block (bare `tool(...)` calls resolving
  against an implicit `self`) has **no** Python equivalent — recommended
  an explicit `register=lambda dsl: dsl.tool(...)` callable parameter
  instead, a real, unavoidable call-site-shape divergence, not an
  implementation detail.
- **`08_the_repl_loop`** introduces `Boukensha.repl`/`Repl` and makes
  `Agent` persist its final reply into `Context` (needed for multi-turn
  history). Found two real, good additions to port faithfully (a
  cwd-`.boukensha` config-resolution tier; a friendlier `401` `ApiError`
  message) — **both of which get silently reverted one step later**, see
  `09_global_executable` below.
- **`09_global_executable`** packages BOUKENSHA as a real installable
  command (`boukensha.gemspec`, `bin/boukensha`, `boukensha_loader.rb`'s
  three-tier env-var/rc-file/bundled-default resolution). This step has
  **no `examples/` directory and no `bin/ruby/09_global_executable`
  launcher anywhere in the repo** — confirmed real, not an oversight — so
  its Python plan is the one exception in this whole series with no
  `examples/example.py`/launcher in its target layout. Found three real
  regressions relative to `08_the_repl_loop`, each judged differently:
  the friendlier 401 message is dropped with no visible rationale
  (recommended **not** replicating — this is the one place in the `06`–
  `10` chain where "port faithfully" is explicitly overridden, same
  category as `04_api_client`'s `PROMPTS_DIR` call); the cwd-`.boukensha`
  tier is dropped with a plausible "a global command should behave the
  same regardless of cwd" rationale (recommended replicating, flagged as
  a judgment call); the REPL banner's API-key/config-dir validation is
  dropped entirely (recommended replicating for fidelity to this exact
  step, but flagged prominently — this is the **exact regression** behind
  the real `09_global_executable` debugging session earlier in this
  repo's history, where a missing `~/.boukensha/` produced a hard crash
  instead of a banner warning). Also designed the one genuinely novel
  mechanism in this series: loading an arbitrary `BOUKENSHA_PATH` step's
  Python source by exact file path via `importlib.util.spec_from_file_
  location` + manual `sys.modules` registration, avoiding any `sys.path`-
  precedence ambiguity with the installed package's own bundled default.
  **Decided 2026-07-28:** the Python console script is named
  `boukensha-py`, not `boukensha` — the Ruby gem already installs a real
  `boukensha` executable on this machine, and the two are meant to coexist
  for comparison rather than fight over `$PATH` order. `pyproject.toml`'s
  `[project.scripts]` entry, and every README/CLI-output reference, use
  `boukensha-py`.
- **`10_standard_tool_library`** adds `Tools::FileSystem`/`Tools::Shell`/
  `Tools::Mud`, `Context#working_dir`, and `working_dir:`/
  `allowed_commands:`/`shell_timeout:`/`mud:` kwargs on `Boukensha.run`/
  `.repl`. Good news: this step **restores** `09_global_executable`'s
  dropped banner validation (confirms `09`'s regression really was
  temporary, not a permanent product decision) and adds a MUD status line.
  The major scoping finding: `Tools::Mud` depends on the separate
  `mud_manager` gem (`week0_explore/mud_manager` — a ~690-line telnet
  session/CircleMUD-command-builder library) which **has no Python port
  and no plan anywhere in this series** — recommended treating `mud_
  manager`'s Python port as its own standalone package with its own
  future plan document, out of scope for this plan, which only designs
  `Tools::Mud`'s registration/wiring layer against `mud_manager`'s
  existing (Ruby) public shape. Also found a false README claim ("the
  evolution of step 9's `WorkingDirectory`") — no such module exists
  anywhere in `09_global_executable`; `FileSystem` is wholly new here.

### Loose threads for whoever ports these

- **Blocking dependency:** `Tools::Mud` in `10_standard_tool_library`
  cannot be implemented for real (only faked/mocked for its own unit
  tests) until `mud_manager` has a Python port. That port doesn't exist
  and isn't planned in this series — write that plan first, or in
  parallel, before attempting a real `10_standard_tool_library`
  implementation.
- None of `06`–`10` exist under `week1_baseline/python/` yet, and neither
  do `03`–`05` — these are plans only, all five and the earlier three plan
  on top of each other in a chain with no real Python code underneath any
  of them yet. The next porting session should implement in order
  (`03` → `04` → `05` → `06` → `07` → `08` → `09` → `10`), since each
  plan's "unchanged copy" claims assume the previous step's *planned* tree
  is what actually gets built — if an earlier step's real implementation
  diverges from its plan, re-check every later plan's assumptions against
  the real code, not the plan text, before trusting them.
- Three separate "port faithfully vs. fix" judgment calls were made across
  `08`/`09` (the 401 message, the cwd-config tier, the banner validation)
  that land on different sides of the line for different reasons — a
  future session implementing these steps should re-confirm each
  independently rather than assuming a single blanket policy applies to
  all Ruby-side regressions encountered in this series.

---

## 03_prompt_builder / 04_api_client / 05_agent_loop — planned, not yet ported (2026-07-27)

Plans: [`03_prompt_builder`](03_prompt_builder), [`04_api_client`](04_api_client),
[`05_agent_loop`](05_agent_loop)

Written by examining the Ruby sources directly (`diff`-ing each step
against its predecessor to isolate real changes from README boilerplate)
rather than against an existing Python port, since none of the three exist
in `week1_baseline/python/` yet. Each plan follows the established
Purpose / Reference files / Target layout / File-by-file mapping /
Behavioural rules / Design decisions / Testing / Open questions structure
from `00_config`–`02_the_registry`.

Notable findings surfaced while planning (full detail in each plan file):

- **`03_prompt_builder`** introduces `PromptBuilder` and five
  `Backends::*` classes (payload serialization only — no HTTP yet). Found
  a real Ruby quirk: `PromptBuilder#to_messages` always calls the backend
  with one argument, but three of five backends require two — never
  triggered because `example.rb` only calls `to_api_payload`. Recommend
  porting the quirk faithfully and pinning it with a test. Also flagged: no
  Python translation for Ruby's `self.model_info`(class method)/
  `model_info`(instance method) name reuse — proposed renaming the
  class-level lookup to `lookup_model`.
- **`04_api_client`** introduces `Client` (stdlib-only HTTP, retries,
  `ApiError`). Found a real **bug**, not a quirk: `config.rb`'s
  `PROMPTS_DIR` gains an extra `../` and resolves to a directory that
  doesn't exist (`ruby/prompts`, vs. the correct `ruby/04_api_client/
  prompts`) — silently masked today because `.boukensha/settings.toml` sets
  `prompt_override.system = true`. Recommended the Python port **not**
  replicate this one, unlike other Ruby-side idiosyncrasies this series has
  otherwise preserved. Also found `urlopen` raises on non-2xx where Ruby's
  `Net::HTTP` returns a response object — needs explicit unification in the
  retry logic, not just a mechanical translation.
- **`05_agent_loop`** introduces `Agent` (the tool-calling loop) and a
  normalized `{stop_reason, content}` response shape every backend must
  produce via new `parse_response`/`_assistant_message`/`_assistant_parts`
  methods. Found `LoopError` is defined in `errors.rb` but never actually
  raised anywhere in this step (dead code, ported for structural parity
  only). Flagged a real Ruby/Python truthiness trap: `@max_output_tokens ?
  ... : {}` relies on Ruby's `0`-is-truthy semantics, which needs an
  explicit `is not None` check in Python rather than a naive truthy check.

### Loose threads for whoever ports these

- None of `03`–`05` exist under `week1_baseline/python/` yet — these are
  plans only. The next session should implement `03_prompt_builder` first
  (the others build directly on it) and update this file's status column
  as each lands, following the `## <step> — done (<date>)` write-up
  pattern established below for `00`–`02`.
- All three plans assume `02_the_registry`'s Python tree as the unchanged
  carry-forward baseline (`config.py`/`tool.py`/`message.py`/`context.py`/
  `registry.py`/`tasks/*.py`) — if anything in that tree changes before
  `03_prompt_builder` is actually implemented, re-check these plans' "unchanged
  copy" assumptions against the real files rather than trusting the plan
  text blindly.

---

## 02_the_registry — done (2026-07-26)

Plan: [`docs/plans/python_port/02_the_registry`](02_the_registry)

Ported `Boukensha::Registry`/`UnknownToolError` to
`week1_baseline/python/02_the_registry/`, a fully self-contained `uv`
project. Confirmed via `diff` that `config.rb`/`tool.rb`/`message.rb`/
`context.rb`/`tasks/*.rb` are byte-identical to `01_struct_skeleton`'s copies,
so they were copied forward unchanged again; only `registry.py` and an
addition to `errors.py` (`UnknownToolError`) are new.

### Decisions made (answers to the plan's open questions)

1. **`Registry.tool`'s `block` is a plain keyword-only `Callable` parameter,
   confirmed** — not a decorator. Ruby's trailing `do |direction:| ... end`
   block has no Python equivalent; passing a `lambda` as `block=` at the
   call site matches how `01_struct_skeleton`'s `example.py` already passes
   callables to `Tool.block`.
2. **Symbol/string `transform_keys` gotcha dropped entirely, confirmed.**
   Ruby's `dispatch` converts string-keyed args to symbol keys before
   calling the block (a deliberate pedagogical gotcha per the Ruby README).
   Python dict keys are always `str` and `**args` unpacks them straight into
   keyword arguments, so there is nothing to simulate — the Python
   `dispatch` just does `tool.block(**args)` directly.
3. **`UnknownToolError` lives in the existing `errors.py`, confirmed**,
   alongside `ConfigError` — matches Ruby's `errors.rb` holding both
   concerns once it exists. This one's a straight 1:1 port since Ruby
   already gives it a real, specific name (unlike `ArgumentError →
   ConfigError` back in `00_config`).

### What exists now

```
week1_baseline/python/02_the_registry/
  pyproject.toml, uv.lock, .python-version (3.14), .gitignore, README.md
  src/boukensha/
    __init__.py     # exports Config, ConfigError, Context, Message, Player,
                     # Registry, Task, Tool, UnknownToolError
    config.py        # unchanged copy from 01_struct_skeleton
    errors.py        # ConfigError (unchanged) + new UnknownToolError
    tool.py           # unchanged copy from 01_struct_skeleton
    message.py        # unchanged copy from 01_struct_skeleton
    context.py         # unchanged copy from 01_struct_skeleton
    registry.py         # Registry: tool(name, *, description, parameters=None,
                         # block=None) / dispatch(name, args=None)
    tasks/              # unchanged copy from 01_struct_skeleton
  prompts/system.md     # unchanged copy from 01_struct_skeleton
  examples/example.py   # 1:1 port of example.rb; verified identical output
  tests/
    test_config.py, test_tasks.py, test_tool.py, test_message.py,
    test_context.py     # unchanged copies from 01_struct_skeleton
    test_registry.py    # new, 5 cases

week1_baseline/bin/python/02_the_registry   # new launcher
```

### Verified

- `./week1_baseline/bin/python/02_the_registry` run from repo root produces
  output matching `./week1_baseline/bin/ruby/02_the_registry` line-for-line,
  except the already-documented `params=['direction']` vs.
  `params=[:direction]` divergence (no Python symbol syntax).
- `uv run pytest -v` — 41/41 passing.
- `uv run ruff check src examples tests` — clean.

### Known upstream README inconsistencies noted (no action needed)

- The Ruby README's "Run Example" section points at a stale
  `./week1_baseline/bin/01_the_registry` path; the real, working script is
  `week1_baseline/bin/ruby/02_the_registry` (confirmed by running it).
- The Ruby README's expected output still shows a `budget=8192` field that
  `context.rb` doesn't implement — same gap already noted under
  `01_struct_skeleton`.

### Loose threads for the next step

- `config.py`/`tool.py`/`message.py`/`context.py`/`tasks/*.py` now exist
  verbatim in `00_config`, `01_struct_skeleton`, **and**
  `02_the_registry`. Same hand-sync burden as before if the Ruby side ever
  changes one of these — now three places to update instead of two.

---

## 01_struct_skeleton — done (2026-07-26)

Plan: [`docs/plans/python_port/01_struct`](01_struct)

Ported `Boukensha::Tool`/`Message`/`Context` to
`week1_baseline/python/01_struct_skeleton/`, a fully self-contained `uv`
project that copies `config.py`/`errors.py`/`tasks/` forward **unchanged**
from `00_config` (mirroring the Ruby side, where each numbered step is its
own independent gem with its own copy of `lib/boukensha/{config,tasks}.rb` —
there is no shared Ruby gem or Python uv-workspace linking steps together).

### Decisions made (answers to the plan's open questions)

1. **Duplication over sharing, confirmed.** Each Python step directory stays
   a standalone `uv` project; `01_struct_skeleton` does not depend on
   `00_config`'s package via path dependency. Same hand-sync maintenance
   cost the Ruby side already accepts.
2. **`context.rb` (not the README) is the spec for `Context`, confirmed.**
   The Ruby `README.md` documents a `token_budget` field and `to_s` examples
   like `#<Context turns=2 tools=1 budget=8192>`, but the actual `context.rb`
   has no such field/behaviour, and `example.rb`'s real output never prints
   a budget. Ported with no `token_budget` field; flagged as a known
   upstream README/code inconsistency, out of scope to fix here.
3. **`Tool.__repr__`'s `params=` renders as `['direction']`, confirmed** —
   Ruby's symbol-keyed hash prints `[:direction]`; Python has no symbols, so
   `list(parameters.keys())` is the accepted, documented divergence.

### What exists now

```
week1_baseline/python/01_struct_skeleton/
  pyproject.toml, uv.lock, .python-version (3.14), .gitignore, README.md
  src/boukensha/
    __init__.py     # exports Config, ConfigError, Context, Message, Player, Task, Tool
    config.py        # unchanged copy from 00_config
    errors.py        # unchanged copy from 00_config
    tool.py           # Tool: @dataclass(name, description, parameters, block)
    message.py        # Message: @dataclass(role, content, tool_use_id=None)
    context.py         # Context: task, system, messages, tools + register_tool/add_message
    tasks/            # unchanged copy from 00_config (base.py, player.py)
  prompts/system.md   # unchanged copy from 00_config
  examples/example.py # 1:1 port of example.rb; verified identical output
  tests/
    test_config.py, test_tasks.py   # unchanged copies from 00_config (code didn't change)
    test_tool.py, test_message.py, test_context.py   # new, 15 cases total

week1_baseline/bin/python/01_struct_skeleton   # new launcher
```

### Verified

- `./week1_baseline/bin/python/01_struct_skeleton` run from repo root
  produces output matching `./week1_baseline/bin/ruby/01_struct_skeleton`
  line-for-line, except the documented `params=['direction']` vs.
  `params=[:direction]` divergence (no Python symbol syntax).
- `uv run pytest -v` — 36/36 passing.
- `uv run ruff check src examples tests` — clean.

### Loose threads for the next step

- `config.py`/`errors.py`/`tasks/*.py` now exist verbatim in both
  `00_config` and `01_struct_skeleton`. If a future Ruby-side change touches
  `Config`/`Task`/`Player`, remember to port it into **both** Python
  directories (same as the settings.yaml/.toml sync burden noted under
  `00_config`) — there's no automated check keeping the duplicates in sync.

---

## 00_config — done (2026-07-26)

Plan: [`docs/plans/python_port/00_config`](00_config)

Ported `Boukensha::Config` and `Boukensha::Tasks::Base/Player` to a standalone
`uv`-managed Python package at `week1_baseline/python/00_config/`, following
the tooling conventions already established by
`week0_explore/circlemud-world-parser` (uv, hatchling, `src/` layout, ruff,
pytest, Python 3.14).

### Decisions made (answers to the plan's open questions)

1. **Settings format switched from YAML to TOML.** Python stdlib has no YAML
   parser but does have `tomllib` (3.11+), so TOML lets the Python side
   honor the "stdlib first" goal the way Ruby does with its stdlib `yaml`.
   This is a deliberate, permanent divergence: Ruby reads `settings.yaml`,
   Python reads `settings.toml`. Both files now live side-by-side in
   `.boukensha/` and are kept in sync by hand.
2. **Package name:** `boukensha`, top-level, repo-wide — future ports
   (`mud_manager`, later steps) are expected to live under the same
   `boukensha` package rather than getting separate packages per step.
3. **`Task` stays classmethod-only**, mirroring Ruby's "never instantiated,
   settings passed explicitly" shape, rather than switching to instances or
   dependency injection.
4. **Directory layout:** `src/boukensha/...` (modern Python packaging
   convention), not a flat `boukensha/` mirroring Ruby's `lib/` layout.
5. **Launcher scripts split by language**, both under `week1_baseline/bin/`:
   `bin/ruby/00_config` (moved from the old single `bin/00_config`) and
   `bin/python/00_config` (new). Both are kept side-by-side indefinitely —
   no plan yet to retire the Ruby line.
6. **Errors:** Ruby's `ArgumentError` → Python's own
   `boukensha.errors.ConfigError`, so config problems are catchable
   specifically rather than as a bare `ValueError`.

### What exists now

```
week1_baseline/python/00_config/
  pyproject.toml, uv.lock, .python-version (3.14), .gitignore, README.md
  src/boukensha/
    __init__.py          # exports Config, ConfigError, Task, Player
    config.py             # Config: dir resolution, tasks(), dig(), mud_* accessors
    errors.py             # ConfigError
    tasks/
      __init__.py
      base.py             # Task: abstract classmethod-only base
      player.py           # Player(Task): task_name() == "player"
  prompts/system.md        # copied verbatim from the Ruby side
  examples/example.py      # 1:1 port of example.rb; verified identical output
  tests/
    test_config.py         # 11 cases
    test_tasks.py           # 10 cases

week1_baseline/bin/ruby/00_config     # moved from week1_baseline/bin/00_config
week1_baseline/bin/python/00_config   # new

.boukensha/settings.toml   # new, TOML twin of the existing settings.yaml
```

### Verified

- `./week1_baseline/bin/python/00_config` run from repo root produces output
  matching `./week1_baseline/bin/ruby/00_config` line-for-line (against the
  real local `.boukensha/` dir, including the `prompt_override` reading the
  user's `prompts/player/system.md`).
- `uv run pytest -v` — 21/21 passing.
- `uv run ruff check src examples tests` — clean.

### Not ported / explicitly out of scope

- `mud_manager` (`week0_explore/mud_manager`, the Ruby telnet-session gem) —
  not yet folded into a numbered `week1_baseline` step on the Ruby side, so
  there's no Ruby spec to port against yet. Gets its own plan once it lands
  there.
- Anything beyond `00_config` — `week2_capable` is still an empty
  placeholder (`.keep` only) on the Ruby side, so there is nothing later to
  port yet.

### Loose threads for the next step

- The two settings files (`settings.yaml` / `settings.toml`) are maintained
  by hand in parallel. If a future Ruby-side schema change lands in
  `settings.yaml`, remember to mirror it into `settings.toml` — there's no
  automated check that they stay in sync.
- No decision yet on whether/when the Ruby line gets retired vs. kept
  permanently side-by-side (see decision 5 above) — revisit once more steps
  are ported and it's clearer whether Python is becoming the primary line.
