from boukensha.backends.ollama_cloud import OllamaCloud
from boukensha.context import Context
from boukensha.message import Message


def make_backend(model="gemma4:31b-cloud"):
    return OllamaCloud(api_key="key-test", model=model)


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


def test_to_payload_shape():
    backend = make_backend()
    ctx = Context(system="be nice")
    payload = backend.to_payload(ctx, max_output_tokens=512)
    assert payload["model"] == "gemma4:31b-cloud"
    assert payload["stream"] is False


def test_headers_and_url():
    backend = make_backend()
    assert backend.headers == {"Content-Type": "application/json", "Authorization": "Bearer key-test"}
    assert backend.url == "https://ollama.com/api/chat"


def test_estimate_cost_none_unpriced():
    backend = make_backend()
    assert backend.estimate_cost(input_tokens=1000, output_tokens=1000) is None


def test_usage_level_present():
    backend = make_backend()
    assert backend.usage_level == "medium"


def test_to_payload_tools_override_used_instead_of_computed():
    backend = make_backend()
    ctx = Context(system="be nice")
    payload = backend.to_payload(ctx, tools=["override"])
    assert payload["tools"] == ["override"]


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
