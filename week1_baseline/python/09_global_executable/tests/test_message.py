from boukensha.message import Message


def test_fields_are_accessible_and_mutable():
    message = Message("user", "hello")
    assert message.role == "user"
    assert message.content == "hello"
    assert message.tool_use_id is None

    message.content = "goodbye"
    assert message.content == "goodbye"


def test_repr_omits_tag_when_no_tool_use_id():
    message = Message("assistant", "hi there")
    assert repr(message) == "#<Message role=assistant content=hi there...>"


def test_repr_includes_tag_when_tool_use_id_present():
    message = Message("tool_result", "You move north.", "toolu_01X")
    assert repr(message) == "#<Message role=tool_result [toolu_01X] content=You move north....>"


def test_repr_truncates_content_to_61_chars():
    long_content = "x" * 100
    message = Message("user", long_content)
    assert repr(message) == f"#<Message role=user content={'x' * 61}...>"


def test_str_matches_repr():
    message = Message("user", "hello")
    assert str(message) == repr(message)
