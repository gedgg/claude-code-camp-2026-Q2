from boukensha.tool import Tool


def test_fields_are_accessible_and_mutable():
    tool = Tool("move", "Move the player", {"direction": {"type": "string"}}, lambda direction: direction)
    assert tool.name == "move"
    assert tool.description == "Move the player"
    assert tool.parameters == {"direction": {"type": "string"}}
    assert callable(tool.block)

    tool.name = "attack"
    assert tool.name == "attack"


def test_default_parameters_and_block():
    tool = Tool("look", "Look around")
    assert tool.parameters == {}
    assert tool.block is None


def test_repr_truncates_description_to_41_chars():
    long_description = "x" * 100
    tool = Tool("look", long_description, {"a": {}, "b": {}})
    text = repr(tool)
    assert text == f"#<Tool name=look description={'x' * 41} params=['a', 'b']>"


def test_str_matches_repr():
    tool = Tool("look", "Look around the current room")
    assert str(tool) == repr(tool)
