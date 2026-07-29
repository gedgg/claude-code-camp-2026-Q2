from boukensha import backends
from boukensha.agent import Agent
from boukensha.client import Client
from boukensha.config import Config
from boukensha.context import Context
from boukensha.errors import ApiError, ConfigError, UnknownToolError, UnsupportedModelError
from boukensha.logger import Logger
from boukensha.message import Message
from boukensha.prompt_builder import PromptBuilder
from boukensha.registry import Registry
from boukensha.tasks import Player, Task
from boukensha.tool import Tool

__all__ = [
    "Agent",
    "ApiError",
    "Client",
    "Config",
    "ConfigError",
    "Context",
    "Logger",
    "Message",
    "Player",
    "PromptBuilder",
    "Registry",
    "Task",
    "Tool",
    "UnknownToolError",
    "UnsupportedModelError",
    "backends",
    "debug",
    "get_config",
    "is_debug",
    "is_quiet",
    "loud",
    "quiet",
]

_quiet = False
_debug = False
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def quiet() -> None:
    global _quiet
    _quiet = True


def loud() -> None:
    global _quiet
    _quiet = False


def is_quiet() -> bool:
    return _quiet


def debug() -> None:
    global _debug
    _debug = True


def is_debug() -> bool:
    return _debug
