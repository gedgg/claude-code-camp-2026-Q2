import os

from boukensha import backends, tools
from boukensha.agent import Agent
from boukensha.client import Client
from boukensha.config import PROMPTS_DIR, Config
from boukensha.context import Context
from boukensha.errors import ApiError, ConfigError, LoopError, UnknownToolError, UnsupportedModelError
from boukensha.logger import Logger
from boukensha.message import Message
from boukensha.prompt_builder import PromptBuilder
from boukensha.registry import Registry
from boukensha.repl import Repl
from boukensha.run_dsl import RunDSL
from boukensha.tasks import Player, Task
from boukensha.tool import Tool
from boukensha.version import VERSION

__all__ = [
    "VERSION",
    "Agent",
    "ApiError",
    "Client",
    "Config",
    "ConfigError",
    "Context",
    "Logger",
    "LoopError",
    "Message",
    "Player",
    "PromptBuilder",
    "Registry",
    "Repl",
    "RunDSL",
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
    "repl",
    "run",
    "tools",
]

_quiet = False
_debug = False
_config: Config | None = None

_API_KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama_cloud": "OLLAMA_API_KEY",
}

_BACKEND_CLASSES = {
    "anthropic": backends.Anthropic,
    "openai": backends.OpenAI,
    "gemini": backends.Gemini,
    "ollama_cloud": backends.OllamaCloud,
}


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


def _mud_opts_from_config(cfg: Config) -> dict | None:
    """Build a mud options dict from config (used when mud=None is passed
    to run()/repl()). Returns None if no MUD host is configured."""
    if not (cfg.mud_host and cfg.mud_username):
        return None

    return {
        "host": cfg.mud_host,
        "port": cfg.mud_port,
        "name": cfg.mud_username,
        "password": cfg.mud_password,
    }


def run(
    *,
    task: str,
    system: str | None = None,
    model: str | None = None,
    backend: str | None = None,
    api_key: str | None = None,
    ollama_host: str = "http://localhost:11434",
    log: str | None = None,
    max_output_tokens: int | None = None,
    working_dir=None,
    allowed_commands: list[str] | None = None,
    shell_timeout: int = 30,
    mud: dict | bool | None = None,
    register=None,
) -> str:
    """The top-level entry point. Wires together every primitive so the
    caller only has to describe *what* to do, not *how* to plumb it.

        result = boukensha.run(
            task="Summarise src/boukensha/__init__.py",
            register=lambda dsl: dsl.tool(
                "read_file",
                description="Read a file from disk",
                parameters={"path": {"type": "string", "description": "File path"}},
                block=lambda *, path: Path(path).read_text(),
            ),
        )

    Options:
      task:         (required) The user message to hand the agent.
      system:       System prompt. Defaults to the player task's configured prompt.
      model:        Model name. Defaults to the player task's configured model.
      backend:      "anthropic" (default), "openai", "gemini", "ollama", or "ollama_cloud".
      api_key:      API key for the chosen backend. Defaults to the matching
                    ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / OLLAMA_API_KEY
                    env var (loaded from .boukensha/.env). Not needed for "ollama".
      ollama_host:  Ollama base URL. Defaults to "http://localhost:11434".
      log:          Optional JSONL path override. Defaults to .boukensha/sessions/<session-id>.jsonl.
      max_output_tokens: Per-reply output cap. Defaults to the task's configured value (1024).
      working_dir:      Roots all tool calls to this directory (default: os.getcwd()). Registers
                        boukensha.tools.file_system (pwd, list_directory, read_file, write_file,
                        delete_file, search_files) and boukensha.tools.shell (run_command)
                        automatically. Pass working_dir=False to opt out entirely.
      allowed_commands: List of shell-executable names the agent is allowed to run via
                        run_command. None (default) permits everything. Pass [] to disable
                        run_command entirely.
      shell_timeout:    Seconds before a run_command is killed (default 30).
      mud:              Dict of MUD connection options — registers all MUD gameplay tools and
                        keeps a single session alive across every tool call. When None (default),
                        config.mud_* values are used if mud_host is set in settings.toml. Pass
                        mud=False to disable entirely.
      register:     Optional callable receiving a RunDSL instance, for registering tools.
    """
    cfg = get_config()  # loads .env; populates os.environ
    task_class = Player
    task_settings = cfg.tasks(task_class.task_name())
    if system is None:
        system = task_class.system_prompt(
            task_settings, user_prompts_dir=cfg.user_prompts_dir, default_prompts_dir=PROMPTS_DIR
        )
    if model is None:
        model = task_class.model(task_settings)
    if backend is None:
        backend = task_class.provider(task_settings)
    if api_key is None:
        api_key = os.environ.get(_API_KEY_ENV_VARS.get(backend, ""))
    if working_dir is None:
        working_dir = os.getcwd()

    ctx = Context(task=task_class, system=system, working_dir=working_dir)
    registry = Registry(ctx)

    if working_dir:
        tools.file_system.register(registry, working_dir=working_dir)
        tools.shell.register(registry, working_dir=working_dir, timeout=shell_timeout, allowed_commands=allowed_commands)

    # mud=None means "use config if host is set"; mud=False means "skip entirely"
    resolved_mud = None if mud is False else (mud or _mud_opts_from_config(cfg))
    if resolved_mud:
        tools.mud.register(registry, **resolved_mud)

    if register is not None:
        register(RunDSL(registry))

    if backend == "ollama":
        be = backends.Ollama(host=ollama_host, model=model)
    elif backend in _BACKEND_CLASSES:
        be = _BACKEND_CLASSES[backend](api_key=api_key, model=model)
    else:
        raise ConfigError(f'Unknown backend "{backend}". Use "anthropic", "openai", "gemini", "ollama", or "ollama_cloud".')

    builder = PromptBuilder(ctx, be)
    client = Client(builder)
    effective_max_iterations = task_class.max_iterations(task_settings)
    effective_max_output_tokens = (
        max_output_tokens if max_output_tokens is not None else task_class.max_output_tokens(task_settings)
    )
    logger = Logger(
        log=log,
        snapshot={
            "task": task_class.task_name(),
            "max_iterations": effective_max_iterations,
            "max_output_tokens": effective_max_output_tokens,
            "model": model,
            "provider": backend,
        },
    )
    agent = Agent(
        context=ctx,
        registry=registry,
        builder=builder,
        client=client,
        logger=logger,
        task_settings=task_settings,
        max_iterations=effective_max_iterations,
        max_output_tokens=effective_max_output_tokens,
    )

    try:
        ctx.add_message("user", task)
        return agent.run()
    finally:
        logger.close()


def repl(
    *,
    system: str | None = None,
    model: str | None = None,
    backend: str | None = None,
    api_key: str | None = None,
    ollama_host: str = "http://localhost:11434",
    log: str | None = None,
    max_output_tokens: int | None = None,
    working_dir=None,
    allowed_commands: list[str] | None = None,
    shell_timeout: int = 30,
    mud: dict | bool | None = None,
    register=None,
) -> None:
    """Interactive REPL — see boukensha.run for full option documentation."""
    cfg = get_config()
    task_class = Player
    task_settings = cfg.tasks(task_class.task_name())
    if system is None:
        system = task_class.system_prompt(
            task_settings, user_prompts_dir=cfg.user_prompts_dir, default_prompts_dir=PROMPTS_DIR
        )
    if model is None:
        model = task_class.model(task_settings)
    if backend is None:
        backend = task_class.provider(task_settings)
    if api_key is None:
        api_key = os.environ.get(_API_KEY_ENV_VARS.get(backend, ""))
    if working_dir is None:
        working_dir = os.getcwd()

    ctx = Context(task=task_class, system=system, working_dir=working_dir)
    registry = Registry(ctx)

    if working_dir:
        tools.file_system.register(registry, working_dir=working_dir)
        tools.shell.register(registry, working_dir=working_dir, timeout=shell_timeout, allowed_commands=allowed_commands)

    resolved_mud = None if mud is False else (mud or _mud_opts_from_config(cfg))
    if resolved_mud:
        tools.mud.register(registry, **resolved_mud)

    if register is not None:
        register(RunDSL(registry))

    if backend == "ollama":
        be = backends.Ollama(host=ollama_host, model=model)
    elif backend in _BACKEND_CLASSES:
        be = _BACKEND_CLASSES[backend](api_key=api_key, model=model)
    else:
        raise ConfigError(f'Unknown backend "{backend}". Use "anthropic", "openai", "gemini", "ollama", or "ollama_cloud".')

    builder = PromptBuilder(ctx, be)
    client = Client(builder)
    effective_max_iterations = task_class.max_iterations(task_settings)
    effective_max_output_tokens = (
        max_output_tokens if max_output_tokens is not None else task_class.max_output_tokens(task_settings)
    )
    logger = Logger(
        log=log,
        snapshot={
            "task": task_class.task_name(),
            "max_iterations": effective_max_iterations,
            "max_output_tokens": effective_max_output_tokens,
            "model": model,
            "provider": backend,
        },
    )

    try:
        Repl(
            context=ctx,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            task_settings=task_settings,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
            config_dir=cfg.dir,
            provider=backend,
            model=model,
            version=VERSION,
            api_key=api_key,
            mud=resolved_mud,
        ).start()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        logger.close()
