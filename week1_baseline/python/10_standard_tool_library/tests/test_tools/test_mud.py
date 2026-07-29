import sys
import types

import pytest

from boukensha.context import Context
from boukensha.registry import Registry


class FakeSessionError(Exception):
    pass


class FakeSession:
    """No real socket — a plain in-memory double implementing the interface
    boukensha.tools.mud.register() expects from mud_manager.Session."""

    Error = FakeSessionError

    def __init__(self, *, host, port, fail_open=False):
        self.host = host
        self.port = port
        self.is_open = False
        self.sent = []
        self.login_calls = []
        self.drain_calls = 0
        self._fail_open = fail_open

    def open(self):
        if self._fail_open:
            raise FakeSessionError("connection refused")
        self.is_open = True

    def close(self):
        self.is_open = False

    def login(self, name, password):
        self.login_calls.append((name, password))
        return "Welcome!"

    def drain(self):
        self.drain_calls += 1

    def send_command(self, command):
        self.sent.append(command)

    def read_until_prompt(self):
        return f"response to: {self.sent[-1]}"

    def read_until_quiet(self):
        return f"raw response to: {self.sent[-1]}"


def _echo(label):
    def fn(*args, **kwargs):
        return f"{label} {args} {kwargs}"

    return fn


class FakePrimitives:
    look = staticmethod(_echo("look"))
    examine = staticmethod(_echo("examine"))
    info_self = staticmethod(_echo("info_self"))
    flee = staticmethod(_echo("flee"))
    set_position = staticmethod(_echo("set_position"))
    track = staticmethod(_echo("track"))
    attack = staticmethod(_echo("attack"))
    skill_strike = staticmethod(_echo("skill_strike"))
    consider = staticmethod(_echo("consider"))
    say_local = staticmethod(_echo("say_local"))
    say_targeted = staticmethod(_echo("say_targeted"))
    say_channel = staticmethod(_echo("say_channel"))
    get = staticmethod(_echo("get"))
    drop = staticmethod(_echo("drop"))
    put = staticmethod(_echo("put"))
    equip = staticmethod(_echo("equip"))
    consume = staticmethod(_echo("consume"))
    cast = staticmethod(_echo("cast"))
    use_magic_item = staticmethod(_echo("use_magic_item"))
    shop = staticmethod(_echo("shop"))
    practice = staticmethod(_echo("practice"))
    save_char = staticmethod(_echo("save_char"))

    @staticmethod
    def move(direction):
        if direction not in ("north", "south", "east", "west", "up", "down"):
            raise ValueError(f"invalid direction: {direction}")
        return f"move {direction}"


@pytest.fixture
def fake_mud_manager(monkeypatch):
    """Injects a fake mud_manager module into sys.modules so
    boukensha.tools.mud's deferred `import mud_manager` picks it up, then
    restores sys.modules afterward so other tests never see it."""
    fake_module = types.SimpleNamespace(Session=FakeSession, primitives=FakePrimitives)
    monkeypatch.setitem(sys.modules, "mud_manager", fake_module)
    return fake_module


def make_registry_and_session(fake_mud_manager, **register_kwargs):
    from boukensha.tools import mud

    ctx = Context()
    registry = Registry(ctx)
    mud.register(registry, name="Gandalf", password="secret", **register_kwargs)
    # register() constructs its own Session via mud_manager.Session(...) — recover
    # it via the closure captured in one of the registered tools' dispatch, by
    # calling mud_status which reports on that exact session.
    return registry


def test_auto_connects_at_registration_time(fake_mud_manager):
    registry = make_registry_and_session(fake_mud_manager)
    assert registry.dispatch("mud_status") == "connected to localhost:4000"


def test_auto_connect_failure_is_swallowed_and_registration_still_completes(fake_mud_manager, capsys):
    class FailingSession(FakeSession):
        def __init__(self, *, host, port):
            super().__init__(host=host, port=port, fail_open=True)

    fake_mud_manager.Session = FailingSession

    from boukensha.tools import mud

    ctx = Context()
    registry = Registry(ctx)
    mud.register(registry, name="Gandalf", password="secret")  # must not raise

    assert registry.dispatch("mud_status") == "disconnected"
    assert "MUD auto-connect failed" in capsys.readouterr().err


def test_gameplay_tool_returns_not_connected_guard_when_disconnected(fake_mud_manager):
    class NeverOpensSession(FakeSession):
        def __init__(self, *, host, port):
            super().__init__(host=host, port=port, fail_open=True)

    fake_mud_manager.Session = NeverOpensSession

    from boukensha.tools import mud

    ctx = Context()
    registry = Registry(ctx)
    mud.register(registry, name="Gandalf", password="secret")

    assert registry.dispatch("look") == "error: not connected — call mud_connect first"
    assert registry.dispatch("move", {"direction": "north"}) == "error: not connected — call mud_connect first"


def test_mud_connect_reports_already_connected_when_open(fake_mud_manager):
    registry = make_registry_and_session(fake_mud_manager)
    result = registry.dispatch("mud_connect")
    assert result == "already connected to localhost:4000"


def test_move_dispatches_through_primitives_when_connected(fake_mud_manager):
    registry = make_registry_and_session(fake_mud_manager)
    result = registry.dispatch("move", {"direction": "north"})
    assert result == "response to: move north"


def test_invalid_direction_argument_error_surfaces_as_error_string(fake_mud_manager):
    registry = make_registry_and_session(fake_mud_manager)
    result = registry.dispatch("move", {"direction": "sideways"})
    assert result == "error: invalid direction: sideways"


def test_flee_practice_save_character_send_raw_have_no_argument_error_guard(fake_mud_manager):
    # These four don't wrap their Primitives call in try/except ValueError in
    # the Ruby source either — matching that exactly, not uniformly adding
    # the guard to every tool.
    registry = make_registry_and_session(fake_mud_manager)

    assert registry.dispatch("flee") == "response to: flee () {}"
    assert registry.dispatch("practice") == "response to: practice (None,) {}"
    assert registry.dispatch("save_character") == "response to: save_char () {}"
    assert registry.dispatch("send_raw", {"command": "who"}) == "raw response to: who"


def test_disconnect_and_status(fake_mud_manager):
    registry = make_registry_and_session(fake_mud_manager)
    assert registry.dispatch("mud_disconnect") == "disconnected"
    assert registry.dispatch("mud_disconnect") == "already disconnected"
    assert registry.dispatch("mud_status") == "disconnected"
