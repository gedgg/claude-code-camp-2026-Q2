import pytest

from boukensha.context import Context
from boukensha.errors import UnknownToolError
from boukensha.registry import Registry


def test_tool_registers_on_context_and_returns_tool():
    ctx = Context()
    registry = Registry(ctx)

    tool = registry.tool(
        "move",
        description="Move the player",
        parameters={"direction": {"type": "string"}},
        block=lambda *, direction: direction,
    )

    assert ctx.tools["move"] is tool
    assert tool.name == "move"
    assert tool.description == "Move the player"


def test_tool_coerces_name_to_str_and_defaults_parameters():
    ctx = Context()
    registry = Registry(ctx)

    tool = registry.tool(123, description="numeric name")
    assert tool.name == "123"
    assert tool.parameters == {}


def test_dispatch_calls_registered_tool_with_kwargs():
    ctx = Context()
    registry = Registry(ctx)
    registry.tool("shout", description="shout", block=lambda *, message: message.upper())

    result = registry.dispatch("shout", {"message": "dragon spotted"})
    assert result == "DRAGON SPOTTED"


def test_dispatch_with_no_args_calls_tool_with_none():
    ctx = Context()
    registry = Registry(ctx)
    registry.tool("look", description="look around", block=lambda: "a torch-lit corridor")

    assert registry.dispatch("look") == "a torch-lit corridor"


def test_dispatch_raises_unknown_tool_error_with_matching_message():
    ctx = Context()
    registry = Registry(ctx)

    with pytest.raises(UnknownToolError, match="No tool registered as 'flee'"):
        registry.dispatch("flee")
