from __future__ import annotations

from boukensha.errors import ApiError


class Agent:
    # Default iteration ceiling. The *enforced* value comes from the
    # max_iterations constructor arg (sourced from Config at the run/repl
    # path), which falls back to this constant. 0 (or None) disables the
    # ceiling.
    MAX_ITERATIONS = 25

    # The wind-down call is deliberately short and cheap.
    WRAP_UP_OUTPUT_TOKENS = 400
    WRAP_UP_DIRECTIVE = (
        "You have reached your action limit for this turn. Do not call any more tools.\n"
        "Briefly summarize what you accomplished, what is still unfinished, and the\n"
        "single next action you would take."
    )

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        task_settings: dict | None = None,
        max_iterations: int | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self._context = context
        self._registry = registry
        self._builder = builder
        self._client = client
        self._max_iterations = self._resolve_max_iterations(task_settings, max_iterations)
        self._max_output_tokens = self._resolve_max_output_tokens(task_settings, max_output_tokens)
        self._iteration = 0

    def run(self) -> str:
        while True:
            # Limits are *trigger thresholds*, not hard caps: once we reach one
            # we stop starting new work iterations and make exactly one
            # terminal wind-down call instead of raising.
            if self._iteration_limit_reached():
                return self._wrap_up("max_iterations")

            self._iteration += 1
            print(f"[iteration {self._iteration}/{self._max_iterations}]")

            response = self._client.call(**self._call_opts())
            parsed = self._builder.parse_response(response)

            if parsed["stop_reason"] == "tool_use":
                self._handle_tool_calls(parsed["content"])
            else:
                return self._extract_text(parsed["content"])

    def _resolve_max_iterations(self, task_settings: dict | None, explicit: int | None) -> int:
        if explicit is not None:
            return int(explicit)
        if task_settings and hasattr(self._context.task, "max_iterations"):
            return self._context.task.max_iterations(task_settings)
        return self.MAX_ITERATIONS

    def _resolve_max_output_tokens(self, task_settings: dict | None, explicit: int | None) -> int | None:
        if explicit is not None:
            return explicit
        if task_settings and hasattr(self._context.task, "max_output_tokens"):
            return self._context.task.max_output_tokens(task_settings)
        return None

    def _iteration_limit_reached(self) -> bool:
        return self._max_iterations > 0 and self._iteration >= self._max_iterations

    def _call_opts(self) -> dict:
        # Per-call options shared by every model round-trip of the turn.
        # NOTE: an explicit `is not None` check, not Python truthiness — Ruby's
        # `@max_output_tokens ? ... : {}` only treats nil/false as falsy, so a
        # (nonsensical but possible) 0 would still populate call_opts in Ruby.
        return {"max_output_tokens": self._max_output_tokens} if self._max_output_tokens is not None else {}

    def _wrap_up(self, reason: str) -> str:
        # One final, tools-disabled model call so the agent ends the turn in
        # character rather than aborting. Runs *outside* the counted loop: it
        # never re-checks the limits (so it cannot re-trigger) and does not
        # increment self._iteration. Falls back to a deterministic message if
        # the call fails.
        self._context.add_message("user", self.WRAP_UP_DIRECTIVE)
        try:
            response = self._client.call(tools=[], max_output_tokens=self.WRAP_UP_OUTPUT_TOKENS)
            text = self._extract_text(self._builder.parse_response(response)["content"])
            return text if text.strip() else self._fallback_message(reason)
        except ApiError:
            return self._fallback_message(reason)

    def _fallback_message(self, reason: str) -> str:
        return (
            f"I reached my {self._max_iterations}-action limit for this turn before finishing "
            f"({reason}). Ask me to continue and I'll pick up from here."
        )

    @staticmethod
    def _extract_text(content: list) -> str:
        return "".join(b["text"] for b in content if b["type"] == "text")

    def _handle_tool_calls(self, content: list) -> None:
        self._context.add_message("assistant", content)

        for block in content:
            if block["type"] != "tool_use":
                continue

            name = block["name"]
            args = block["input"]
            use_id = block["id"]

            print(f"  tool call → {name}({args})")
            result = self._registry.dispatch(name, args)
            print(f"  tool result → {str(result)[:61]}")

            self._context.add_message("tool_result", str(result), tool_use_id=use_id)
