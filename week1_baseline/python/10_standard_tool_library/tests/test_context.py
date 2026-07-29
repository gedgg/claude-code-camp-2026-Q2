from boukensha.context import Context
from boukensha.tasks.player import Player
from boukensha.tool import Tool


def test_starts_empty():
    ctx = Context()
    assert ctx.task is None
    assert ctx.system is None
    assert ctx.working_dir is None
    assert ctx.messages == []
    assert ctx.tools == {}
    assert ctx.tool_count == 0
    assert ctx.turn_count == 0


def test_working_dir_is_expanded_to_an_absolute_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = Context(working_dir="relative_dir")
    assert ctx.working_dir == (tmp_path / "relative_dir").resolve()


def test_working_dir_none_when_falsy():
    assert Context(working_dir=None).working_dir is None
    assert Context(working_dir=False).working_dir is None
    assert Context(working_dir="").working_dir is None


def test_register_tool_stores_by_name():
    ctx = Context()
    tool = Tool("move", "Move the player")
    ctx.register_tool(tool)
    assert ctx.tools["move"] is tool
    assert ctx.tool_count == 1


def test_add_message_appends_message():
    ctx = Context()
    ctx.add_message("user", "hello")
    ctx.add_message("assistant", "hi", tool_use_id="toolu_01X")
    assert ctx.turn_count == 2
    assert ctx.messages[0].role == "user"
    assert ctx.messages[1].tool_use_id == "toolu_01X"


def test_clear_messages_wipes_history_keeps_tools_and_system():
    ctx = Context(task=Player, system="be helpful")
    ctx.register_tool(Tool("move", "Move the player"))
    ctx.add_message("user", "hello")
    ctx.add_message("assistant", "hi")

    ctx.clear_messages()

    assert ctx.messages == []
    assert ctx.turn_count == 0
    assert ctx.tools["move"] is not None
    assert ctx.tool_count == 1
    assert ctx.system == "be helpful"


def test_repr_with_task_calls_task_name():
    ctx = Context(task=Player, system="be helpful")
    assert repr(ctx) == "#<Context task=player turns=0 tools=0>"


def test_repr_with_no_task_shows_none():
    ctx = Context()
    assert repr(ctx) == "#<Context task=None turns=0 tools=0>"


def test_str_matches_repr():
    ctx = Context(task=Player)
    assert str(ctx) == repr(ctx)
