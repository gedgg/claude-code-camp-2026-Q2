# 09 · Global Executable (Python)

Python port of `week1_baseline/ruby/09_global_executable`. See
[`docs/plans/python_port/09_global_executable`](../../../docs/plans/python_port/09_global_executable)
for the full port plan and the decisions behind the differences from Ruby
called out below.

Package BOUKENSHA as a real, installable command — `boukensha-py` — that
works from any directory on the machine.

**Command name: `boukensha-py`, not `boukensha`.** The Ruby gem already
installs a real `boukensha` executable on this machine. Both
implementations are meant to coexist for side-by-side comparison, so the
Python console script is named `boukensha-py` deliberately, avoiding any
`$PATH`-order ambiguity between the two.

**No `examples/` directory, no `bin/python/09_global_executable`
launcher** — a deliberate divergence from every other step in this port,
matching the Ruby source exactly (`ruby/09_global_executable` has neither
either — confirmed by checking `week1_baseline/bin/ruby/`, which jumps
from `08_the_repl_loop` straight to `10_standard_tool_library`). The
deliverable *is* the installed command.

## Install

```bash
cd week1_baseline/python/09_global_executable
uv tool install .
# or: pip install . / pipx install .
```

After that, `boukensha-py` is on your `$PATH` and works from any directory.

## Switching steps with `BOUKENSHA_PATH`

The loader resolves in this order:

| Priority | Source | Example |
|----------|--------|---------|
| 1 | `BOUKENSHA_PATH` env var | `BOUKENSHA_PATH=~/Sites/boukensha_py/07_the_run_dsl boukensha-py` |
| 2 | `~/.boukensharc` file | `echo ~/Sites/boukensha_py/08_the_repl_loop > ~/.boukensharc` |
| 3 | Bundled default | just run `boukensha-py` |

`BOUKENSHA_PATH` must point to a step folder containing `src/boukensha/__init__.py`.

```bash
# step 8 (interactive REPL)
BOUKENSHA_PATH=~/Sites/boukensha_py/08_the_repl_loop boukensha-py

# step 2 doesn't have a REPL — the loader tells you how to run it
BOUKENSHA_PATH=~/Sites/boukensha_py/02_the_registry boukensha-py
# => boukensha-py: the step at .../02_the_registry
#    does not support the interactive REPL (added in step 7).
#    Run its examples directly, e.g.:
#      python .../02_the_registry/examples/example.py
```

## Debug mode

```bash
BOUKENSHA_DEBUG=1 boukensha-py
# => [boukensha-py] loading from: /path/to/step
```

## The key idea

The package is just a **wrapper and a default**. All the teaching material
stays in the numbered step folders exactly as it was. `boukensha_loader.py`
doesn't copy or symlink anything — it just knows where to look, and loads
the resolved `boukensha/__init__.py` by exact file path.

## Known regressions relative to `08_the_repl_loop` (and how this port handles each)

Three things changed relative to `08_the_repl_loop`, matching Ruby's own
history at this exact step — each judged independently, not treated as a
blanket "always revert" or "always keep" policy:

1. **The friendlier `401` `ApiError` message is *not* reverted here** —
   `client.py` keeps `08_the_repl_loop`'s addition. No rationale for
   dropping it is visible anywhere in the Ruby source or README, so this
   Python port doesn't replicate that regression (same category as
   `04_api_client`'s `PROMPTS_DIR` fix earlier in this series).
2. **The cwd-`.boukensha` config-resolution tier *is* reverted** — back to
   env-var-or-`~/.boukensha` only. This one has a plausible rationale tied
   to this step's own purpose: a *global* command arguably should resolve
   to the same config regardless of which directory you happen to be
   standing in when you type it, rather than picking up an ambient
   `.boukensha/` in the cwd.
3. **The REPL banner's API-key/config-dir validation *is* reverted** —
   the banner now just prints raw values with no existence/blankness
   checks, matching Ruby's real regression at this exact step. This one is
   flagged, not silently accepted: it directly caused a real debugging
   session in this repo's history (a missing `~/.boukensha/` produced a
   hard crash instead of a banner warning, because there was no validation
   left to catch it). Restored again in `10_standard_tool_library` —
   confirming Ruby's own regression here really was temporary.

## The novel mechanism: exact-path module loading

`BOUKENSHA_PATH` needs to load an arbitrary, independent step's
`boukensha` package under the same import name — without colliding with
this installation's own bundled `boukensha` package. `boukensha_loader.py`
does this with `importlib.util.spec_from_file_location`, registering the
result in `sys.modules["boukensha"]` **before** executing it (so the
loaded package's own internal `from boukensha.x import Y` submodule
imports resolve against that exact instance) — no `sys.path` mutation, no
precedence ambiguity with the installed package.

`_bundled_lib()` resolves the bundled default's own path via
`importlib.util.find_spec("boukensha")` rather than a hardcoded
`Path(__file__).parent / "boukensha"` — this matters in practice, not just
in theory: under `uv sync`'s **editable install** (which this very project
uses for local development), `boukensha_loader.py` is a real file in
`site-packages/` (via `force-include`), but the `boukensha/` package it
"sits next to" is redirected via a `.pth` file back to `src/boukensha/`,
so the two aren't physically adjacent. `find_spec` resolves correctly
regardless of whether the install is editable, a normal wheel install, or
anything else — this was caught by actually running the installed
`boukensha-py` command end-to-end, not just by unit tests with fakes.

## Code Layout

| File | Purpose |
|------|---------|
| `pyproject.toml` | `[project.scripts] boukensha-py = "boukensha_loader:main"`; `force-include`s `boukensha_loader.py` into the wheel root |
| `src/boukensha_loader.py` | `resolve()`, `_load_boukensha_module()`, `load_and_start_repl()`, `main()` |
| `src/boukensha/version.py` | `VERSION = "0.9.0"` |
| `src/boukensha/client.py` | No change from `08_the_repl_loop` — 401 message kept |
| `src/boukensha/config.py` | cwd-`.boukensha` tier removed |
| `src/boukensha/repl.py` | Banner validation removed |
| `src/boukensha/{...}.py` | Otherwise unchanged from `08_the_repl_loop` |
| `tests/test_boukensha_loader.py` | New |

## Development

```bash
cd week1_baseline/python/09_global_executable
uv sync
uv run pytest -v
uv run ruff check src tests
```

Manual end-to-end verification (recommended over unit tests alone for this
step, since the whole point is the installed command):

```bash
uv tool install .   # or use .venv/bin/boukensha-py directly after `uv sync`
boukensha-py
BOUKENSHA_PATH=../08_the_repl_loop BOUKENSHA_DEBUG=1 boukensha-py
```
