from __future__ import annotations

from collections.abc import Callable

from boukensha.context import Context
from boukensha.errors import UnknownToolError
from boukensha.tool import Tool


class Registry:
    def __init__(self, context: Context) -> None:
        self.context = context

    def tool(self, name: str, *, description: str, parameters: dict | None = None, block: Callable | None = None) -> Tool:
        tool = Tool(str(name), description, parameters or {}, block)
        self.context.register_tool(tool)
        return tool

    def dispatch(self, name: str, args: dict | None = None):
        args = args or {}
        tool = self.context.tools.get(str(name))
        if not tool:
            raise UnknownToolError(f"No tool registered as '{name}'")
        return tool.block(**args)
