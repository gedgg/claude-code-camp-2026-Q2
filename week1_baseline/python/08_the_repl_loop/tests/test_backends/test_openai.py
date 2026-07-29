from boukensha.backends.openai import OpenAI
from boukensha.context import Context
from boukensha.message import Message


def make_backend(model="gpt-5.4-mini"):
    return OpenAI(api_key="key-test", model=model)


def test_to_messages_prepends_system_message():
    backend = make_backend()
    result = backend.to_messages("be nice", [Message("user", "hi")])
    assert result[0] == {"role": "system", "content": "be nice"}
    assert result[1] == {"role": "user", "content": "hi"}


def test_to_messages_tool_result_uses_tool_call_id():
    backend = make_backend()
    messages = [Message("tool_result", "42", tool_use_id="call_1")]
    result = backend.to_messages(None, messages)
    assert result[1] == {"role": "tool", "tool_call_id": "call_1", "content": "42"}


def test_to_payload_uses_max_completion_tokens():
    backend = make_backend()
    ctx = Context(system="be nice")
    payload = backend.to_payload(ctx, max_output_tokens=512)
    assert payload["max_completion_tokens"] == 512
    assert "max_tokens" not in payload


def test_headers_and_url():
    backend = make_backend()
    assert backend.headers == {"Content-Type": "application/json", "Authorization": "Bearer key-test"}
    assert backend.url == "https://api.openai.com/v1/chat/completions"


def test_to_payload_tools_override_used_instead_of_computed():
    backend = make_backend()
    ctx = Context(system="be nice")
    payload = backend.to_payload(ctx, tools=["override"])
    assert payload["tools"] == ["override"]


def test_parse_response_text_only_is_end_turn():
    backend = make_backend()
    response = {"choices": [{"message": {"content": "hi"}}]}

    assert backend.parse_response(response) == {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "hi"}],
    }


def test_parse_response_tool_calls_use_real_id_and_decodes_json_string_arguments():
    backend = make_backend()
    response = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {"name": "move", "arguments": '{"direction": "north"}'},
                        }
                    ],
                }
            }
        ]
    }

    parsed = backend.parse_response(response)
    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"] == [{"type": "tool_use", "id": "call_1", "name": "move", "input": {"direction": "north"}}]


def test_assistant_message_round_trip_encodes_arguments_as_json_string():
    backend = make_backend()
    blocks = [{"type": "tool_use", "id": "call_1", "name": "move", "input": {"direction": "north"}}]

    result = backend.to_messages(None, [Message("assistant", blocks)])
    assert result[1] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "move", "arguments": '{"direction": "north"}'}}
        ],
    }


def test_assistant_message_round_trip_string_content():
    backend = make_backend()
    result = backend.to_messages(None, [Message("assistant", "plain text")])
    assert result[1] == {"role": "assistant", "content": "plain text"}
