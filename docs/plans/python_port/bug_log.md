# Bug Log

Every real bug found and fixed on the **Ruby side** while operating as the
porting/debugging agent across 2026-07-28 – 2026-07-29, plus a concrete
plan for checking whether each one has an equivalent risk in the
**Python port** (`week1_baseline/python/`) — and if so, how to locate,
fix, and test it there.

This is a companion to [`context.md`](context.md), which tracks the port
itself step-by-step. This file tracks *bugs*, cutting across steps.

Status legend: 🔴 open · 🟡 investigated, no action needed · 🟢 fixed/verified

---

## Bug index

| ID | Summary | Where found | Status (Ruby) | Python port risk |
|----|---------|-------------|----------------|-------------------|
| [BUG-01](#bug-01-boukensharc-contained-a-keyvalue-line-instead-of-a-plain-path) | `~/.boukensharc` held `KEY=value` instead of a plain path | `09_global_executable` | 🟢 fixed | Same loader logic ported to `boukensha_loader.py` — needs a targeted test |
| [BUG-02](#bug-02-missing-hboukensha-config-directory) | Missing `~/.boukensha` (no `settings.yaml`, no `prompts/`) | `09_global_executable` | 🟢 fixed | **Confirmed present in Python step 09 too** (faithfully reverted banner validation) — already fixed again in step 10, needs a live check |
| [BUG-03](#bug-03-mud_manager-gem-not-installed) | `mud_manager` gem never installed | `10_standard_tool_library` | 🟢 fixed (Ruby side) | No Python `mud_manager` port exists at all — bigger, already-tracked gap |
| [BUG-04](#bug-04-stale-cross-machine-gemfilelock) | Stale, cross-machine `Gemfile.lock` (built on `arm64-darwin-23`, run on Linux) | `10_standard_tool_library` | 🟢 fixed | `uv.lock` equivalent risk — needs a portability check across all 8 Python steps |
| [BUG-05](#bug-05-global-boukensha-resolved-to-the-wrong-gem-version) | Global `boukensha` resolved to gem v0.9.0 instead of v0.10.0 | global executable | 🟢 fixed | `boukensha-py` isn't installed globally yet — same failure mode will apply once it is; needs a plan for verifying upgrades |
| [BUG-06](#bug-06-stale-pre-refactor-gem-build-artifact-the-big-one) | **Stale, pre-refactor `.gem` build artifact** — sent `system: null` to Anthropic, got rejected | `10_standard_tool_library` | 🟢 fixed | **Direct structural equivalent**: an editable `uv sync` install can just as easily go stale relative to `src/` edits — highest-priority check |
| [BUG-07](#bug-07-log_viz-suspended-process--wrong-sessions-directory) | `log_viz`: suspended process holding port 4567 + reading the wrong sessions directory | `week1_baseline/log_viz` | 🟢 fixed | No Python `log_viz` exists — not applicable, noted for completeness only |

---

## BUG-01: `~/.boukensharc` contained a `KEY=value` line instead of a plain path

**Symptom:** `boukensha` (Ruby global executable) aborted immediately with
`~/.boukensharc points to BOUKENSHA_DIR=... but no lib/boukensha.rb was
found there.`

**Root cause:** `~/.boukensharc` is supposed to hold a single bare path to
a step folder. It instead contained `BOUKENSHA_DIR=/home/gedgg/projects/
claude-code-camp-2026-Q2/.boukensha` — a `KEY=value` line, apparently
copied by mistake from the `bin/ruby/10_standard_tool_library` launcher
script's own `export BOUKENSHA_DIR=...` convention. `BOUKENSHA_DIR` is a
*separate*, unrelated env var (the config directory), not something
`.boukensharc` (which selects a *step*) understands.

**Fix:** Cleared the file's contents (empty is treated the same as
"unset," falling through to the bundled default) rather than deleting it
outright.

**Verified:** `boukensha` (no `BOUKENSHA_PATH`, no env override) resolved
to the bundled default step correctly afterward.

---

## BUG-02: Missing `~/.boukensha` config directory

**Symptom:** After fixing BUG-01, `boukensha` failed differently:
`tasks.player.model is required in settings.yaml (ArgumentError)`.

**Root cause:** `~/.boukensha/` (the default config directory for the
*global* executable) didn't exist at all — every other step's `bin/ruby/*`
launcher script explicitly sets `BOUKENSHA_DIR` to the repo-root
`.boukensha/`, but the global executable has no such wrapper and genuinely
needs its config at the real default location. Compounding this: step 9's
REPL banner (a real, confirmed Ruby-side regression — see
[`09_global_executable`](09_global_executable)'s plan) had dropped the
API-key/config-dir validation that would have shown a clear
`"✗ directory not found"` warning instead of a confusing crash three
layers deep.

**Fix:** Copied the working config (`.env`, `settings.yaml`, `prompts/`)
from the repo-root `.boukensha/` into `~/.boukensha/`.

**Verified:** `boukensha` booted into the REPL correctly from any
directory afterward.

---

## BUG-03: `mud_manager` gem not installed

**Symptom:** `bin/ruby/10_standard_tool_library` crashed with `Could not
find mud_manager-0.1.0 in locally installed gems`.

**Root cause:** `10_standard_tool_library`'s gemspec depends on
`mud_manager` (`week0_explore/mud_manager`), a separate, unpublished gem
that only exists as a locally-built `.gem` file in this repo — it was
never installed.

**Fix:** `gem install --local week0_explore/mud_manager/mud_manager-0.1.0.gem`.

**Verified:** Required alongside BUG-04's fix (see next) to get
`bundle install` fully working.

---

## BUG-04: Stale, cross-machine `Gemfile.lock`

**Symptom:** Even after BUG-03's fix, `bundle install` in
`10_standard_tool_library` failed with permission errors trying to write
to `/var/lib/gems/3.3.0`, then with a Bundler-version mismatch, then with
"mud_manager (0.1.0)... has been removed" once it tried to fetch from
rubygems.org.

**Root cause:** `Gemfile.lock` had `PLATFORMS: arm64-darwin-23, ruby` and
`BUNDLED WITH 2.5.19` — it was generated on a different machine (a Mac),
not this Linux/WSL2 sandbox, and it also predates whatever Bundler version
is installed here. It's part of this repo's own uncommitted working-tree
state, not something to preserve byte-for-byte.

**Fix:** Deleted the stale `Gemfile.lock` and regenerated it fresh via
`GEM_HOME=<user gem dir> bundle install`, which resolved cleanly against
the now-locally-installed `mud_manager` and `dotenv`.

**Verified:** `bash bin/ruby/10_standard_tool_library` ran end-to-end with
no environment overrides needed, exit code 0.

---

## BUG-05: Global `boukensha` resolved to the wrong gem version

**Symptom:** MUD interactions via the global `boukensha` command showed
`tool_count: 0` in the session log — the agent had no tools at all and
responded like a generic chatbot ("Google Maps... Yelp...").

**Root cause:** `gem list boukensha -a` showed only `0.9.0` installed —
`09_global_executable`, which has **no** `Tools::FileSystem`/`Shell`/`Mud`
modules and no `working_dir:`/`mud:` keyword arguments at all. The gem was
never upgraded to `10_standard_tool_library` (`0.10.0`), where those tools
actually live.

**Fix:** `gem install
week1_baseline/ruby/10_standard_tool_library/boukensha-0.10.0.gem`.
RubyGems resolves the newest installed version by default, so the global
`boukensha` command started using `0.10.0`.

**Verified:** Banner showed `v0.10.0`, 34 tools listed. (This fix alone
was necessary but *not sufficient* — see BUG-06.)

---

## BUG-06: Stale, pre-refactor `.gem` build artifact (the big one)

**Symptom:** After BUG-05's fix, the banner correctly showed v0.10.0 and
34 tools, but every real API call failed: `API request failed after 1
attempt (400): {"system":"Input should be a valid array"}`.

**Root cause — the most significant bug found in this whole session.**
The `.gem` file sitting in `10_standard_tool_library/` (which BUG-05
installed) was **not built from the current source tree**. It was a
leftover build from an *early draft* of the course, predating the
`Tasks::Player`/task-based-settings refactor that the current
`lib/boukensha/` checkout has. Confirmed by literally unpacking the `.gem`
file and diffing it against the checkout:

- Old `Config`: `provider_type`, `model`, `system_override?`, `silent?`,
  reads a **flat `<BOUKENSHA_DIR>/system.md`** file.
- Current `Config`: `tasks(:player)`, per-task `provider`/`model`, reads
  `<BOUKENSHA_DIR>/prompts/player/system.md`.

Since the real `~/.boukensha/` was set up to match the *current* schema,
the stale gem's `cfg.system_prompt` (looking for a flat `system.md` that
doesn't exist) silently returned `nil` → `Context.new(system: nil, ...)`
→ the JSON payload's `"system"` field was **literally `null`** → Anthropic
rejected it. The confusing `"should be a valid array"` wording is just
Anthropic's schema-validator phrasing for an explicit `null` where a
`string | array` was expected — a real, if misleading, upstream error
message, not a bug in this repo's request-building itself once the actual
byte-for-byte request was captured and inspected.

Diagnostic method that found this (worth reusing): rather than trusting
"the payload looks right," intercept `Net::HTTP#request` at runtime via a
monkey-patched `alias_method` and dump the *literal bytes* sent to the
wire to a file — this is what revealed `"system": null` when a manual
reconstruction of "the same" payload had (misleadingly) succeeded.

**Fix:**
1. `gem build boukensha.gemspec` from the *current* `10_standard_tool_library`
   checkout, overwriting the stale `.gem` file with a fresh one.
2. Confirmed the fresh build's unpacked `lib/` now diffs identically
   against the checkout (zero differences).
3. `gem uninstall boukensha -v 0.10.0` then reinstalled the freshly built
   `.gem`.

**Verified:** Real, live, multi-turn MUD session — the agent connected,
looked around the Temple of Midgaard, checked exits, and navigated
room-to-room searching for a bakery. Full tool-call trace confirmed in
the session log.

**Known related gap, not yet fixed (low priority):** the gemspec's
`spec.files` list still never includes `prompts/**/*`, so a freshly built
gem still ships **no default system prompt of its own** — it currently
works only because `prompt_override.system = true` in `settings.yaml`
makes it use the user-override path instead. If that override were ever
turned off, `Config::PROMPTS_DIR` (computed relative to the installed
gem's own `lib/`) would point at a directory that was never packaged, and
`system_prompt` would silently go back to `nil`. Offered to fix the
gemspec; not yet actioned.

---

## BUG-07: `log_viz` — suspended process + wrong sessions directory

**Symptom:** User reported "port already in use" trying to start `log_viz`,
and separately wondered whether it was showing the latest session runs.

**Root cause (two, unrelated):**
1. Port 4567 was held by an **already-running but suspended** (`T` state)
   Puma process from an earlier terminal (started 11:41 that day,
   presumably paused with Ctrl-Z and forgotten) — not a crash, not a
   zombie, just stopped.
2. `log_viz` defaults to reading `<repo root>/.boukensha/sessions`, but
   the plain global `boukensha` command (no `BOUKENSHA_DIR` override)
   logs to `~/.boukensha/sessions` instead — two genuinely different,
   diverging directories depending on how `boukensha` is invoked.

**Fix:**
1. `kill -CONT <pid>` to resume the suspended process (confirmed alive
   again via a real HTTP request) rather than killing/restarting anything
   unnecessarily.
2. Per the user's request, restarted it anyway with
   `LOG_VIZ_SESSIONS_DIR=~/.boukensha/sessions` so it reads the directory
   that actually receives plain `boukensha` invocations.

**Verified:** New instance responds `HTTP 200` and lists the two most
recent MUD-validation sessions at the top.

**Python port relevance:** none — there is no Python `log_viz` and none
is planned. Included here only for a complete record of this session's
debugging work.

---

## Python Port Investigation Plan

For each Ruby-side bug above with real Python-port relevance, here is how
I'll check whether the equivalent exists, and how I'll fix + test it if
so. Ordered by priority (highest-risk first).

### Priority 1 — BUG-06's direct equivalent: does an installed/editable `boukensha-py` go stale relative to `src/` edits?

**Why this is the top priority:** BUG-06 was the worst bug of the session
precisely *because* it was silent and structural — a built artifact quietly
diverged from source. The Python port has the exact same shape of risk:
`uv sync` creates an **editable** install (a `.pth` redirect into `src/`),
which normally *does* stay in sync automatically — but `boukensha_loader.py`
is `force-include`d as a **physically copied** file into `site-packages/`
(see the `09` bug already documented above in this file's history), so it
can go stale independently of `src/` the same way the Ruby `.gem` did.

**Locate:**
1. In each of `09_global_executable` and `10_standard_tool_library`, diff
   the installed `site-packages/boukensha_loader.py` against the checked-out
   `src/boukensha_loader.py` (`diff <(cat .venv/lib/python*/site-packages/boukensha_loader.py) src/boukensha_loader.py`).
2. Repeat for the `boukensha/` package itself — confirm the `.pth` redirect
   is still pointing at the current `src/boukensha/` (not stale) by checking
   `importlib.util.find_spec("boukensha").origin` resolves inside the
   current checkout, not a copied/cached location.
3. Check whether `uv tool install .` (once run for real, per the deferred
   item already in `context.md`) produces an **editable** or **regular**
   (copied) install — `uv tool install` may default differently than
   `uv sync`. This determines whether the "goes stale silently" risk even
   applies to the eventual global install, or only to the local `.venv`s
   used for testing so far.

**Fix (if found stale):** `uv sync --reinstall-package boukensha` (already
documented as the fix for the exact `09` incident) or `uv tool upgrade
boukensha` / reinstall for a global install.

**Test:** Add a regression check (could be a short manual runbook step
rather than a pytest case, since it's about the *install*, not the code):
after editing `src/boukensha_loader.py`, run the installed console script
and confirm behavior reflects the edit *before* declaring a fix verified —
i.e., bake "did you actually reinstall?" into the verification checklist
for `09`/`10`, the same lesson BUG-06 taught on the Ruby side.

### Priority 2 — BUG-02's equivalent: missing config directory / banner validation gap

**Status: already largely covered**, since the `09`/`10` plans and READMEs
already document that step 9's Python port faithfully reverts the banner
validation (matching Ruby's real regression) and step 10 restores it
(matching Ruby's real fix) — this was a *deliberate, tracked* port
decision, not an undiscovered bug. Still worth a live confirmation pass
since it hasn't been exercised against a genuinely missing config dir.

**Locate/Test:**
1. `mv ~/.boukensha ~/.boukensha.bak` (temporary, reversible) or use a
   scratch `BOUKENSHA_DIR` pointing at an empty directory.
2. Run `09_global_executable`'s `boukensha-py` REPL banner — confirm it
   shows no validation (reproduces Ruby's exact regression) and then
   crashes the same confusing way on the first turn (`ConfigError`, not a
   silent hang).
3. Run `10_standard_tool_library`'s `boukensha-py` REPL banner against the
   same missing directory — confirm it now shows `"✗ directory not
   found"` (the fix), matching Ruby's step-10 restoration.
4. Restore `~/.boukensha` afterward.

**Fix:** None expected — this is a verification pass to confirm the
already-made port decisions actually behave as documented, not a new bug
to fix.

### Priority 3 — BUG-04's equivalent: `uv.lock` portability across machines

**Locate:**
1. For each of the 8 ported steps (`03`–`10`), run `uv lock --check` (or
   delete `uv.lock` and `uv sync` fresh) to confirm the committed lock
   file isn't pinned to a platform/Python build that doesn't match this
   machine — the Ruby equivalent bug (BUG-04) was exactly this kind of
   drift (`arm64-darwin-23` lock used on Linux).
2. Specifically check whether any `uv.lock` files were generated before a
   dependency change (e.g., `python-dotenv` version bumps) landed in a
   `pyproject.toml` without a matching `uv sync` afterward.

**Fix (if found stale):** `uv lock` to regenerate, or `uv sync` to refresh.

**Test:** A quick `for d in week1_baseline/python/*/; do (cd "$d" && uv
sync && uv run pytest -q); done` sweep — this doubles as a full
regression check across every step, not just a lock-file check.

### Priority 4 — BUG-05's equivalent: verifying upgrades once `boukensha-py` is installed globally

**Status:** not yet applicable — `boukensha-py` isn't installed globally
yet (tracked as a deferred item already in `context.md`). This is a
forward-looking plan item, not a current bug to locate.

**Plan for when it's picked up:**
1. `uv tool install .` from `10_standard_tool_library` (per the existing
   deferred-item note).
2. Confirm `uv tool list` shows exactly one `boukensha` entry — unlike
   RubyGems (which happily keeps multiple versions installed side by side
   and silently picks the newest), `uv tool install` typically replaces
   the prior version outright, so BUG-05's specific failure mode (two
   versions coexisting, wrong one active) is less likely to recur — but
   confirm this assumption rather than trust it, since `uv`'s multi-version
   tool behavior wasn't tested in this session.
3. After any future change to `10_standard_tool_library`'s source, test
   the upgrade path explicitly: `uv tool upgrade boukensha` (or
   reinstall), then re-run the same live verification used throughout this
   port (banner version number, tool count, a real API call) rather than
   assuming the global command picked up the change.

### Priority 5 — BUG-03/`mud_manager`'s equivalent

**Status:** already fully tracked as its own, larger, separate item (see
`context.md`'s "Still open" note under the `10` completion log, and the
`10_standard_tool_library` plan's dedicated section on this). No new
locate/fix/test plan needed here beyond what's already written — the
Python-side gap is bigger than BUG-03 was (a whole missing package, not
just an uninstalled one) and already has its own tracked plan: port
`mud_manager` to Python as its own standalone package before `Tools.mud`
can be exercised for real.

### Not applicable

- **BUG-01** (`.boukensharc` malformed content): the Python
  `boukensha_loader.py` port already has equivalent tests
  (`test_rc_file_pointing_to_invalid_path_aborts_without_falling_through`,
  etc.) covering "rc file points somewhere without a valid
  `src/boukensha/__init__.py`" — a `KEY=value` line would hit exactly this
  path (treated as a literal, invalid path) and already aborts correctly.
  No new test needed; noted as already covered.
- **BUG-07** (`log_viz`): no Python equivalent exists or is planned.
