"""Shell registers command-execution tools against a registry.

Tools registered:
  run_command  -- run an arbitrary shell command inside the working directory

Options:
  working_dir:      (required) all commands run with this as their cwd
  timeout:          seconds before a command is killed (default 30)
  allowed_commands: optional list of allowed executable names (e.g. ["ruby", "git"]).
                    When None (the default) all commands are permitted.
                    When set, any command whose first token is not in the list
                    is rejected before execution.

Usage (handled automatically by boukensha.run / boukensha.repl when
working_dir= is set):

    from boukensha.tools import shell
    shell.register(registry, working_dir="/my/project", allowed_commands=["ruby", "bundle", "rspec", "git"])
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def register(registry, *, working_dir: str | Path, timeout: int = 30, allowed_commands: list[str] | None = None) -> None:
    root = Path(working_dir).expanduser().resolve()

    def run_command(*, command: str) -> str:
        # Guard: check the first token against the allow-list when one is set.
        if allowed_commands is not None:
            executable = command.strip().split()[0] if command.strip() else ""
            if executable not in [str(c) for c in allowed_commands]:
                allowed = ", ".join(str(c) for c in allowed_commands)
                return f"error: '{executable}' is not in the allowed-commands list ({allowed})"

        try:
            # shell=True so multi-word commands ("ls -la") work naturally.
            # A nonexistent executable doesn't raise here (the shell itself
            # runs fine) — it surfaces via a nonzero exit code and stderr
            # text instead, same as it would in a real terminal.
            result = subprocess.run(
                command,
                shell=True,
                cwd=root,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as e:
            return f"error: command not found: {e}"
        except subprocess.TimeoutExpired:
            return f"error: command timed out after {timeout}s: {command}"
        except OSError as e:
            return f"error: {e}"

        output = (result.stdout + result.stderr).decode(errors="replace").strip()
        exit_note = "" if result.returncode == 0 else f"\n[exit {result.returncode}]"
        return f"(no output){exit_note}" if not output else f"{output}{exit_note}"

    allowed_note = f" Allowed executables: {', '.join(str(c) for c in allowed_commands)}." if allowed_commands else ""
    registry.tool(
        "run_command",
        description=(
            "Run a shell command inside the working directory and return its combined stdout+stderr output. "
            f"Commands run with a {timeout}-second timeout.{allowed_note}"
        ),
        parameters={
            "command": {
                "type": "string",
                "description": "The shell command to execute (e.g. 'python script.py', 'ls -la', 'git status')",
            }
        },
        block=run_command,
    )
