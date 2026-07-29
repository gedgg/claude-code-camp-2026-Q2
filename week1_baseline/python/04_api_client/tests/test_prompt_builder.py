import pytest

from boukensha.context import Context
from boukensha.prompt_builder import PromptBuilder


class FakeBackend:
    def __init__(self):
        self.headers = {"fake": "header"}
        self.url = "https://example.test/api"
        self.messages_calls = []
        self.tools_calls = []
        self.payload_calls = []

    def to_messages(self, messages):
        self.messages_calls.append(messages)
        return ["messages", messages]

    def to_tools(self, tools):
        self.tools_calls.append(tools)
        return ["tools", tools]

    def to_payload(self, context, *, max_output_tokens=1024):
        self.payload_calls.append((context, max_output_tokens))
        return {"max_output_tokens": max_output_tokens}


def test_to_messages_delegates_with_context_messages():
    ctx = Context()
    ctx.add_message("user", "hi")
    backend = FakeBackend()
    builder = PromptBuilder(ctx, backend)

    result = builder.to_messages()

    assert result == ["messages", ctx.messages]
    assert backend.messages_calls == [ctx.messages]


def test_to_tools_delegates_with_context_tools():
    ctx = Context()
    backend = FakeBackend()
    builder = PromptBuilder(ctx, backend)

    result = builder.to_tools()

    assert result == ["tools", ctx.tools]
    assert backend.tools_calls == [ctx.tools]


def test_to_api_payload_forwards_max_output_tokens_default():
    ctx = Context()
    backend = FakeBackend()
    builder = PromptBuilder(ctx, backend)

    result = builder.to_api_payload()

    assert result == {"max_output_tokens": 1024}
    assert backend.payload_calls == [(ctx, 1024)]


def test_to_api_payload_forwards_explicit_max_output_tokens():
    ctx = Context()
    backend = FakeBackend()
    builder = PromptBuilder(ctx, backend)

    result = builder.to_api_payload(max_output_tokens=256)

    assert result == {"max_output_tokens": 256}
    assert backend.payload_calls == [(ctx, 256)]


def test_headers_and_url_delegate():
    ctx = Context()
    backend = FakeBackend()
    builder = PromptBuilder(ctx, backend)

    assert builder.headers == {"fake": "header"}
    assert builder.url == "https://example.test/api"


def test_to_messages_arity_mismatch_quirk_ollama_style_backend():
    """PromptBuilder.to_messages always calls the backend with one argument.
    Backends whose to_messages takes (system, messages) — Ollama/OllamaCloud/
    OpenAI — raise TypeError if called this way. This pins down a real,
    faithfully-ported Ruby quirk rather than silently fixing it."""

    class TwoArgBackend:
        def to_messages(self, system, messages):
            return (system, messages)

    ctx = Context()
    builder = PromptBuilder(ctx, TwoArgBackend())

    with pytest.raises(TypeError):
        builder.to_messages()
