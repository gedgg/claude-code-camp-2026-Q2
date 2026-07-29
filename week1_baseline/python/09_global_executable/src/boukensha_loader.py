"""Resolves which step folder to load from, then boots the REPL.

Resolution order:
  1. BOUKENSHA_PATH environment variable (selects which *step* lib to load)
  2. ~/.boukensharc  (a file containing a single path)
  3. The boukensha/ package bundled inside this installation (the latest release)

Config directory (settings.toml, .env, system.md) is separate:
  BOUKENSHA_DIR=~/.boukensha  (default; set to override)

Examples:
  boukensha-py                                                                # uses bundled lib + ~/.boukensha
  BOUKENSHA_PATH=~/Sites/boukensha_py/04_api_client boukensha-py              # loads step 4
  BOUKENSHA_DIR=~/projects/mybot/.boukensha boukensha-py                     # custom config dir
  echo ~/Sites/boukensha_py/08_the_repl_loop > ~/.boukensharc && boukensha-py # permanent step default
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _bundled_lib() -> Path:
    """Absolute path to this installation's own bundled boukensha package's
    __init__.py — found via Python's real import machinery (importlib.util.
    find_spec), not a hardcoded "sibling of this file" path. This matters
    because the two aren't always physically adjacent: under an editable
    install (e.g. `uv sync` on this very project), boukensha_loader.py is a
    real file in site-packages but the boukensha/ package it sits "next to"
    is redirected via a .pth file back to src/boukensha/ — so assuming
    Path(__file__).parent / "boukensha" breaks under that (very common,
    very real) install mode. find_spec resolves correctly regardless of
    whether boukensha/ is a physically colocated directory, a .pth-redirected
    editable install, or a normally installed wheel."""
    spec = importlib.util.find_spec("boukensha")
    return Path(spec.origin)


# Absolute path to this installation's own bundled boukensha package.
# A module-level constant (computed once, matching Ruby's BUNDLED_LIB
# constant) — safe because "boukensha" always resolves the same way for the
# lifetime of this process.
BUNDLED_LIB = _bundled_lib()


def resolve() -> Path:
    # 1. Env var wins.
    env_path = os.environ.get("BOUKENSHA_PATH")
    if env_path:
        step_dir = Path(env_path).expanduser().resolve()
        main = step_dir / "src" / "boukensha" / "__init__.py"
        if main.exists():
            return main

        sys.exit(
            "boukensha-py: BOUKENSHA_PATH is set but no src/boukensha/__init__.py found at:\n"
            f"       {step_dir}\n"
            "       Make sure BOUKENSHA_PATH points to a step folder, e.g.:\n"
            "       BOUKENSHA_PATH=~/Sites/boukensha_py/08_the_repl_loop boukensha-py"
        )

    # 2. ~/.boukensharc
    rc = Path("~/.boukensharc").expanduser()
    if rc.exists():
        rc_path = rc.read_text().strip()
        if rc_path:
            step_dir = Path(rc_path).expanduser().resolve()
            main = step_dir / "src" / "boukensha" / "__init__.py"
            if main.exists():
                return main

            sys.exit(
                f"boukensha-py: ~/.boukensharc points to {rc_path}\n"
                "       but no src/boukensha/__init__.py was found there.\n"
                "       Update ~/.boukensharc or remove it to use the bundled default."
            )

    # 3. Bundled default.
    return BUNDLED_LIB


def _load_boukensha_module(main: Path):
    """Loads `main` (a boukensha/__init__.py, possibly outside this
    installation) as the module named "boukensha" by exact file path — the
    Python analogue of Ruby's `require <exact path>`. Avoids any sys.path
    precedence ambiguity with this installation's own bundled package: no
    sys.path mutation happens at all, and the module is registered in
    sys.modules *before* being executed, so its own internal
    `from boukensha.x import Y` submodule imports resolve against this exact
    loaded instance."""
    spec = importlib.util.spec_from_file_location(
        "boukensha", main, submodule_search_locations=[str(main.parent)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["boukensha"] = module
    spec.loader.exec_module(module)
    return module


def load_and_start_repl() -> None:
    main = resolve()
    step_dir = main.parent.parent.parent

    if os.environ.get("BOUKENSHA_DEBUG"):
        print(f"[boukensha-py] loading from: {step_dir}")

    module = _load_boukensha_module(main)

    if not hasattr(module, "repl"):
        sys.exit(
            f"boukensha-py: the step at {step_dir}\n"
            "       does not support the interactive REPL (added in step 7).\n"
            "       Run its examples directly, e.g.:\n"
            f"         python {step_dir}/examples/example.py\n"
            "       Or point BOUKENSHA_PATH at step 7 or later."
        )

    module.repl()


def main() -> None:
    load_and_start_repl()


if __name__ == "__main__":
    main()
