from boukensha.backends.anthropic import Anthropic
from boukensha.context import Context
from boukensha.message import Message
from boukensha.tool import Tool


def make_backend():
    return Anthropic(api_key="sk-test", model="claude-haiku-4-5")


def test_to_messages_user_and_assistant_pass_through():
    backend = make_backend()
    messages = [Message("user", "hello"), Message("assistant", "hi there")]

    assert backend.to_messages(messages) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_to_messages_tool_result_becomes_user_content_block():
    backend = make_backend()
    messages = [Message("tool_result", "42", tool_use_id="toolu_1")]

    assert backend.to_messages(messages) == [
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "42"}],
        }
    ]


def test_to_tools_builds_input_schema():
    backend = make_backend()
    tools = {"move": Tool("move", "Move", {"direction": {"type": "string"}})}

    assert backend.to_tools(tools) == [
        {
            "name": "move",
            "description": "Move",
            "input_schema": {
                "type": "object",
                "properties": {"direction": {"type": "string"}},
                "required": ["direction"],
            },
        }
    ]


def test_to_payload_shape():
    backend = make_backend()
    ctx = Context(system="be nice")
    ctx.add_message("user", "hi")

    payload = backend.to_payload(ctx, max_output_tokens=512)

    assert payload["model"] == "claude-haiku-4-5"
    assert payload["system"] == "be nice"
    assert payload["max_tokens"] == 512
    assert payload["tools"] == []
    assert payload["messages"] == [{"role": "user", "content": "hi"}]


def test_headers_and_url():
    backend = make_backend()
    assert backend.headers == {
        "Content-Type": "application/json",
        "x-api-key": "sk-test",
        "anthropic-version": "2023-06-01",
    }
    assert backend.url == "https://api.anthropic.com/v1/messages"


def test_to_payload_tools_override_used_instead_of_computed():
    backend = make_backend()
    ctx = Context(system="be nice")
    ctx.register_tool(Tool("move", "Move", {}))

    payload = backend.to_payload(ctx, tools=[])

    assert payload["tools"] == []


def test_parse_response_text_only_is_end_turn():
    backend = make_backend()
    response = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "hi"}]}

    assert backend.parse_response(response) == {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "hi"}],
    }


def test_parse_response_tool_use_case():
    backend = make_backend()
    response = {
        "stop_reason": "tool_use",
        "content": [
            {"type": "text", "text": "let me check"},
            {"type": "tool_use", "id": "toolu_1", "name": "move", "input": {"direction": "north"}},
        ],
    }

    parsed = backend.parse_response(response)
    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"] == response["content"]


def test_assistant_message_content_passes_through_string_or_blocks():
    backend = make_backend()
    # Anthropic has no _assistant_message helper — content (string or a list
    # of normalized blocks) passes straight through to_messages unchanged.
    blocks = [{"type": "tool_use", "id": "toolu_1", "name": "move", "input": {"direction": "north"}}]

    assert backend.to_messages([Message("assistant", "plain text")]) == [
        {"role": "assistant", "content": "plain text"}
    ]
    assert backend.to_messages([Message("assistant", blocks)]) == [{"role": "assistant", "content": blocks}]
