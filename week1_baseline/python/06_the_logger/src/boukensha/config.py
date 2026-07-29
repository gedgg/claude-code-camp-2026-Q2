from __future__ import annotations

import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv

# The .boukensha config directory is resolved in this order:
#   1. BOUKENSHA_DIR environment variable
#   2. ~/.boukensha  (default)
DEFAULT_DIR = Path.home() / ".boukensha"

# Default prompts shipped alongside the library code.
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class Config:
    def __init__(self) -> None:
        self.dir = self._resolve_dir()
        self._load_env()
        self.settings = self._load_settings()

    # ---------- tasks -----------------------------------------------------

    def tasks(self, name: str | None = None) -> dict:
        """With no argument: the full ``tasks`` table. With a name: that
        task's settings dict, e.g. ``tasks("player")``."""
        all_tasks = self.dig("tasks") or {}
        return all_tasks.get(name) if name else all_tasks

    @property
    def user_prompts_dir(self) -> Path:
        return self.dir / "prompts"

    # ---------- low-level helpers -------------------------------------------

    def dig(self, *keys: str):
        node = self.settings
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    def __repr__(self) -> str:
        return f"#<Boukensha::Config dir={self.dir} tasks={','.join(self.tasks().keys())}>"

    __str__ = __repr__

    def _resolve_dir(self) -> Path:
        raw = os.environ.get("BOUKENSHA_DIR") or str(DEFAULT_DIR)
        return Path(raw).expanduser().resolve()

    def _load_env(self) -> None:
        env_file = self.dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    def _load_settings(self) -> dict:
        settings_file = self.dir / "settings.toml"
        if not settings_file.exists():
            return {}
        return tomllib.loads(settings_file.read_text()) or {}
