from boukensha.run_dsl import RunDSL


class FakeRegistry:
    def __init__(self):
        self.tool_calls = []

    def tool(self, name, *, description, parameters=None, block=None):
        self.tool_calls.append((name, description, parameters, block))
        return "the-tool"


def test_tool_forwards_all_arguments_to_registry():
    registry = FakeRegistry()
    dsl = RunDSL(registry)
    block = lambda *, path: path

    result = dsl.tool("read_file", description="Read a file", parameters={"path": {"type": "string"}}, block=block)

    assert result == "the-tool"
    assert registry.tool_calls == [("read_file", "Read a file", {"path": {"type": "string"}}, block)]


def test_tool_defaults_parameters_and_block_to_none():
    registry = FakeRegistry()
    dsl = RunDSL(registry)

    dsl.tool("look", description="Look around")

    assert registry.tool_calls == [("look", "Look around", None, None)]
