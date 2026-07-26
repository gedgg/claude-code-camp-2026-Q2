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

Nothing has been committed to git yet — everything below is working-tree
state as of 2026-07-26.

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
