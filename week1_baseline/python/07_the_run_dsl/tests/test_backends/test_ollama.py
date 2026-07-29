from boukensha.backends.ollama import Ollama
from boukensha.context import Context
from boukensha.message import Message
from boukensha.tool import Tool


def make_backend(**kwargs):
    return Ollama(model=kwargs.pop("model", "gemma4"), **kwargs)


def test_to_messages_prepends_system_message():
    backend = make_backend()
    result = backend.to_messages("be nice", [Message("user", "hi")])

    assert result[0] == {"role": "system", "content": "be nice"}
    assert result[1] == {"role": "user", "content": "hi"}


def test_to_messages_tool_result_uses_tool_name():
    backend = make_backend()
    messages = [Message("tool_result", "42", tool_use_id="get_score")]

    result = backend.to_messages(None, messages)

    assert result[1] == {"role": "tool", "tool_name": "get_score", "content": "42"}


def test_to_tools_wraps_function_schema():
    backend = make_backend()
    tools = {"move": Tool("move", "Move", {"direction": {"type": "string"}})}

    assert backend.to_tools(tools) == [
        {
            "type": "function",
            "function": {
                "name": "move",
                "description": "Move",
                "parameters": {
                    "type": "object",
                    "properties": {"direction": {"type": "string"}},
                    "required": ["direction"],
                },
            },
        }
    ]


def test_to_payload_shape_omits_max_output_tokens():
    backend = make_backend()
    ctx = Context(system="be nice")

    payload = backend.to_payload(ctx, max_output_tokens=512)

    assert payload["model"] == "gemma4"
    assert payload["stream"] is False
    assert "max_output_tokens" not in payload
    assert "num_predict" not in payload


def test_headers_and_url_default_host():
    backend = make_backend()
    assert backend.headers == {"Content-Type": "application/json"}
    assert backend.url == "http://localhost:11434/api/chat"


def test_url_uses_custom_host():
    backend = Ollama(host="http://example.test:1234", model="gemma4")
    assert backend.url == "http://example.test:1234/api/chat"


def test_estimate_cost_is_zero_not_none_for_local_models():
    backend = make_backend()
    assert backend.estimate_cost(input_tokens=1000, output_tokens=1000) == 0.0


def test_to_payload_tools_override_used_instead_of_computed():
    backend = make_backend()
    ctx = Context(system="be nice")
    ctx.register_tool(Tool("move", "Move", {}))

    payload = backend.to_payload(ctx, tools=[])
    assert payload["tools"] == []


def test_parse_response_text_only_is_end_turn():
    backend = make_backend()
    response = {"message": {"content": "hi"}}

    assert backend.parse_response(response) == {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "hi"}],
    }


def test_parse_response_tool_calls_reuse_function_name_as_id():
    backend = make_backend()
    response = {
        "message": {
            "content": "",
            "tool_calls": [{"function": {"name": "move", "arguments": {"direction": "north"}}}],
        }
    }

    parsed = backend.parse_response(response)
    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"] == [{"type": "tool_use", "id": "move", "name": "move", "input": {"direction": "north"}}]


def test_assistant_message_round_trip_string_content():
    backend = make_backend()
    result = backend.to_messages(None, [Message("assistant", "plain text")])
    assert result[1] == {"role": "assistant", "content": "plain text"}


def test_assistant_message_round_trip_tool_use_blocks_keeps_arguments_as_dict():
    backend = make_backend()
    blocks = [{"type": "tool_use", "id": "move", "name": "move", "input": {"direction": "north"}}]

    result = backend.to_messages(None, [Message("assistant", blocks)])
    assert result[1] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "move", "arguments": {"direction": "north"}}}],
    }
