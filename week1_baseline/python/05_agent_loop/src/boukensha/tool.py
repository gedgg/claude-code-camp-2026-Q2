from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    block: Callable | None = None

    def __repr__(self) -> str:
        return f"#<Tool name={self.name} description={self.description[:41]} params={list(self.parameters.keys())}>"

    __str__ = __repr__
