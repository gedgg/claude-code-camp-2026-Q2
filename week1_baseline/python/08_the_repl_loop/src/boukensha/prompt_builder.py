from __future__ import annotations


class PromptBuilder:
    """Thin delegator: forwards to whichever backend it's given."""

    def __init__(self, context, backend) -> None:
        self._context = context
        self.backend = backend

    def to_messages(self):
        # NOTE: this calls the backend with a single argument (context.messages).
        # Anthropic/Gemini's to_messages(messages) accept that; Ollama/OllamaCloud/
        # OpenAI's to_messages(system, messages) require two and will raise
        # TypeError here. This mirrors a real arity mismatch in the Ruby source
        # (PromptBuilder#to_messages always calls with one argument) — ported
        # faithfully rather than fixed, since nothing calls this method directly
        # in practice (to_api_payload calls each backend's to_messages correctly).
        return self.backend.to_messages(self._context.messages)

    def to_tools(self):
        return self.backend.to_tools(self._context.tools)

    def to_api_payload(self, *, max_output_tokens: int = 1024, tools: list | None = None):
        return self.backend.to_payload(self._context, max_output_tokens=max_output_tokens, tools=tools)

    def parse_response(self, response: dict) -> dict:
        return self.backend.parse_response(response)

    @property
    def headers(self):
        return self.backend.headers

    @property
    def url(self):
        return self.backend.url
