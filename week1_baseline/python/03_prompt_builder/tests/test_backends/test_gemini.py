from boukensha.backends.gemini import Gemini
from boukensha.context import Context
from boukensha.message import Message
from boukensha.tool import Tool


def make_backend():
    return Gemini(api_key="key-test", model="gemini-2.5-flash")


def test_to_messages_user_passes_through_as_parts():
    backend = make_backend()
    assert backend.to_messages([Message("user", "hello")]) == [{"role": "user", "parts": [{"text": "hello"}]}]


def test_to_messages_assistant_becomes_model_role():
    backend = make_backend()
    assert backend.to_messages([Message("assistant", "hi")]) == [{"role": "model", "parts": [{"text": "hi"}]}]


def test_to_messages_tool_result_becomes_function_response():
    backend = make_backend()
    messages = [Message("tool_result", "42", tool_use_id="get_score")]

    assert backend.to_messages(messages) == [
        {
            "role": "user",
            "parts": [{"functionResponse": {"name": "get_score", "response": {"content": "42"}}}],
        }
    ]


def test_to_tools_empty_when_no_tools():
    backend = make_backend()
    assert backend.to_tools({}) == []


def test_to_tools_wraps_function_declarations():
    backend = make_backend()
    tools = {"move": Tool("move", "Move", {"direction": {"type": "string"}})}

    assert backend.to_tools(tools) == [
        {
            "functionDeclarations": [
                {
                    "name": "move",
                    "description": "Move",
                    "parameters": {
                        "type": "object",
                        "properties": {"direction": {"type": "string"}},
                        "required": ["direction"],
                    },
                }
            ]
        }
    ]


def test_to_payload_shape():
    backend = make_backend()
    ctx = Context(system="be nice")

    payload = backend.to_payload(ctx, max_output_tokens=512)

    assert payload["systemInstruction"] == {"parts": [{"text": "be nice"}]}
    assert payload["contents"] == []
    assert payload["tools"] == []
    assert payload["generationConfig"] == {"maxOutputTokens": 512}


def test_headers_and_url():
    backend = make_backend()
    assert backend.headers == {"Content-Type": "application/json", "x-goog-api-key": "key-test"}
    assert backend.url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
