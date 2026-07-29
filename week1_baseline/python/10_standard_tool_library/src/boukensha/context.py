from __future__ import annotations

from pathlib import Path

from boukensha.message import Message
from boukensha.tasks.base import Task
from boukensha.tool import Tool


class Context:
    def __init__(
        self,
        task: type[Task] | None = None,
        system: str | None = None,
        working_dir: str | Path | None = None,
    ) -> None:
        self.task = task
        self.system = system
        self.working_dir = Path(working_dir).expanduser().resolve() if working_dir else None
        self.messages: list[Message] = []
        self.tools: dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def add_message(self, role: str, content: str, *, tool_use_id: str | None = None) -> None:
        self.messages.append(Message(role, content, tool_use_id))

    def clear_messages(self) -> None:
        """Drop all conversation history, keeping tools and system prompt
        intact. Used by the REPL's `/clear` command."""
        self.messages = []

    @property
    def tool_count(self) -> int:
        return len(self.tools)

    @property
    def turn_count(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        task_name = self.task.task_name() if self.task else None
        return f"#<Context task={task_name} turns={self.turn_count} tools={self.tool_count}>"

    __str__ = __repr__
