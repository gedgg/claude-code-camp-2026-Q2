from __future__ import annotations

import socket
from pathlib import Path

from boukensha.agent import Agent
from boukensha.errors import ApiError, LoopError


class Repl:
    """The interactive session loop.

    Wraps the same primitives as a single boukensha.run() call, but instead
    of running once it stays alive: it reads a task from the user, runs the
    agent, prints the reply, and loops back to the prompt.

    The Context is shared across every turn so conversation history
    accumulates naturally — the agent sees the full transcript each time it
    is called.

    Built-in commands (not sent to the agent):
      /help    print the command list
      /quiet   suppress detailed logging
      /loud    re-enable logging
      /clear   wipe conversation history (tools stay registered)
      /exit    leave the REPL
      /quit    alias for /exit
    """

    PROMPT = "boukensha> "

    HELP = (
        "Commands:\n"
        "  /quiet   suppress logging output\n"
        "  /loud    re-enable logging output\n"
        "  /clear   wipe conversation history (tools stay)\n"
        "  /exit    leave the REPL\n"
        "  /help    show this message"
    )

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        logger,
        config_dir=None,
        provider=None,
        model=None,
        version=None,
        api_key=None,
        mud: dict | None = None,
        task_settings=None,
        max_iterations=None,
        max_output_tokens=None,
    ) -> None:
        self._context = context
        self._registry = registry
        self._builder = builder
        self._client = client
        self._logger = logger
        self._task_settings = task_settings
        self._max_iterations = max_iterations
        self._max_output_tokens = max_output_tokens
        self._config_dir = config_dir
        self._provider = provider
        self._model = model
        self._version = version
        self._api_key = api_key
        self._mud = mud
        self._turn = 0

    def start(self) -> None:
        print(self._banner())

        while True:
            print(self.PROMPT, end="", flush=True)

            try:
                line = input()
            except EOFError:
                break  # EOF / Ctrl-D

            line = line.strip()
            if not line:
                continue

            if line in ("/exit", "/quit"):
                print("Goodbye.")
                break
            if line == "/help":
                print(self.HELP)
                continue
            if line == "/quiet":
                import boukensha

                boukensha.quiet()
                print("(logging suppressed — type /loud to re-enable)")
                continue
            if line == "/loud":
                import boukensha

                boukensha.loud()
                print("(logging enabled)")
                continue
            if line == "/clear":
                self._context.clear_messages()
                self._turn = 0
                print("(conversation history cleared)")
                continue

            self._run_turn(line)

    def _banner(self) -> str:
        # Restores the API-key/config-dir validation that 09_global_executable
        # had dropped — confirms that regression really was temporary, matching
        # Ruby's own history at this exact step.
        key_status = "✗ API key not set" if (not self._api_key or not self._api_key.strip()) else "✓ API key set"
        provider_line = f"{self._provider or 'default'} ({self._model or 'default'})  {key_status}"
        config_exists = bool(self._config_dir) and Path(self._config_dir).is_dir()
        config_line = str(self._config_dir) if config_exists else f"{self._config_dir or '(default)'}  ✗ directory not found"
        ver = self._version or "?.?.?"
        mud_stat = self._mud_status_string()

        return (
            "\n"
            "╔══════════════════════════════════════╗\n"
            f"║  BOUKENSHA MUD Assistant (v{ver}){' ' * (9 - len(ver))}║\n"
            "╚══════════════════════════════════════╝\n"
            f"  config:    {config_line}\n"
            f"  provider:  {provider_line}\n"
            f"  mud:       {mud_stat}\n"
            "\n"
            "  /quiet or /loud   toggle logging\n"
            "  /clear           reset conversation history\n"
            "  /exit or /quit    leave the REPL\n"
        )

    def _mud_status_string(self) -> str:
        # Build the mud status string shown in the banner. Only checks TCP
        # reachability — the tool session auto-connects at startup (in
        # Tools.mud.register), so probing login here would cause a double-login.
        if not self._mud:
            return "(not configured)"

        host = self._mud.get("host") or "localhost"
        port = self._mud.get("port") or 4000
        name = self._mud.get("name")

        return f"{host}:{port}  {self._probe_mud(host, port, name)}"

    @staticmethod
    def _probe_mud(host: str, port: int, name: str | None) -> str:
        try:
            with socket.create_connection((host, port), timeout=3):
                pass
        except OSError:
            return "✗ not reachable"

        return "(Reachable)" if name and str(name).strip() else "(Reachable, no credentials)"

    def _run_turn(self, input_text: str) -> None:
        self._turn += 1
        self._logger.turn(n=self._turn)

        self._context.add_message("user", input_text)

        agent = Agent(
            context=self._context,
            registry=self._registry,
            builder=self._builder,
            client=self._client,
            logger=self._logger,
            task_settings=self._task_settings,
            max_iterations=self._max_iterations,
            max_output_tokens=self._max_output_tokens,
        )
        try:
            result = agent.run()
        except LoopError as e:
            print(f"\n[error] {e}")
            return
        except ApiError as e:
            print(f"\n[error] API call failed: {e}")
            return

        print()
        print(result)
