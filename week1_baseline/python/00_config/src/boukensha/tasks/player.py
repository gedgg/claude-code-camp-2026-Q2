from __future__ import annotations

from boukensha.tasks.base import Task


class Player(Task):
    @classmethod
    def task_name(cls) -> str:
        return "player"
