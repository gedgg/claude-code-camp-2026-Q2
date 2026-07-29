import json
from typing import ClassVar

import pytest

import boukensha
from boukensha.errors import ConfigError

SETTINGS_TOML = """
[tasks.player]
provider = "anthropic"
model = "claude-haiku-4-5"
max_iterations = 3
max_output_tokens = 111
"""


class FakeClient:
    """Records construction (builder) and every call() — used in place of
    the real Client so no network call ever happens in these tests."""

    instances: ClassVar[list] = []

    def __init__(self, builder):
        self.builder = builder
        self.calls = []
        FakeClient.instances.append(self)

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return {"stop_reason": "end_turn", "content": [{"type": "text", "text": "done"}]}


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    (tmp_path / "settings.toml").write_text(SETTINGS_TOML)
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))
    monkeypatch.setattr(boukensha, "_config", None)
    monkeypatch.setattr(boukensha, "Client", FakeClient)
    FakeClient.instances.clear()
    yield tmp_path
    monkeypatch.setattr(boukensha, "_config", None)


def test_defaults_pulled_from_config_when_not_explicit():
    result = boukensha.run(task="hello", api_key="sk-test")

    assert result == "done"
    client = FakeClient.instances[0]
    assert client.builder.backend.model == "claude-haiku-4-5"
    # max_iterations/max_output_tokens from settings.toml flow into Agent via task_settings
    assert client.calls[0] == {"max_output_tokens": 111}


def test_explicit_overrides_win_over_config_defaults():
    result = boukensha.run(
        task="hello",
        system="custom system prompt",
        model="claude-opus-4-8",
        backend="anthropic",
        api_key="sk-test",
        max_output_tokens=999,
    )

    assert result == "done"
    client = FakeClient.instances[0]
    assert client.builder.backend.model == "claude-opus-4-8"
    assert client.calls[0] == {"max_output_tokens": 999}


def test_register_is_invoked_before_backend_is_constructed(monkeypatch):
    order = []

    class TrackingClient(FakeClient):
        def __init__(self, builder):
            order.append("client_constructed")
            super().__init__(builder)

    monkeypatch.setattr(boukensha, "Client", TrackingClient)

    def register(dsl):
        order.append("register_called")
        dsl.tool("noop", description="does nothing", block=lambda: "ok")

    boukensha.run(task="hello", api_key="sk-test", register=register)

    assert order == ["register_called", "client_constructed"]


def test_unknown_backend_raises_before_any_client_call():
    with pytest.raises(ConfigError, match="Unknown backend"):
        boukensha.run(task="hello", backend="not-a-real-backend")

    assert FakeClient.instances == []


def test_logger_is_closed_even_when_agent_run_raises(tmp_path, monkeypatch):
    class RaisingClient(FakeClient):
        def call(self, **kwargs):
            raise RuntimeError("network exploded")

    monkeypatch.setattr(boukensha, "Client", RaisingClient)

    with pytest.raises(RuntimeError):
        boukensha.run(task="hello", api_key="sk-test", log=str(tmp_path / "custom.jsonl"))

    # the log file exists and is a valid, closed file (session_start line written)
    lines = (tmp_path / "custom.jsonl").read_text().splitlines()
    assert json.loads(lines[0])["phase"] == "session_start"


def test_returned_value_is_the_agents_final_text():
    result = boukensha.run(task="hello", api_key="sk-test")
    assert result == "done"


class FakeRepl:
    """Records construction kwargs; .start() runs (or raises) whatever the
    test configured, standing in for the real Repl so no stdin/stdout loop
    is involved in these boukensha.repl() wiring tests."""

    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        FakeRepl.instances.append(self)

    def start(self):
        self.started = True


def test_repl_builds_the_stack_and_starts_it(monkeypatch):
    monkeypatch.setattr(boukensha, "Repl", FakeRepl)
    FakeRepl.instances.clear()

    boukensha.repl(api_key="sk-test")

    assert len(FakeRepl.instances) == 1
    repl_instance = FakeRepl.instances[0]
    assert repl_instance.started is True
    assert repl_instance.kwargs["provider"] == "anthropic"
    assert repl_instance.kwargs["model"] == "claude-haiku-4-5"
    assert repl_instance.kwargs["max_iterations"] == 3
    assert repl_instance.kwargs["max_output_tokens"] == 111


def test_repl_catches_keyboard_interrupt_and_prints_message(monkeypatch, capsys):
    class InterruptingRepl(FakeRepl):
        def start(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(boukensha, "Repl", InterruptingRepl)

    boukensha.repl(api_key="sk-test")  # must not propagate

    assert "Interrupted." in capsys.readouterr().out


def test_repl_closes_logger_even_after_keyboard_interrupt(monkeypatch, tmp_path):
    class InterruptingRepl(FakeRepl):
        def start(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(boukensha, "Repl", InterruptingRepl)

    log_path = tmp_path / "repl-session.jsonl"
    boukensha.repl(api_key="sk-test", log=str(log_path))

    lines = log_path.read_text().splitlines()
    assert json.loads(lines[0])["phase"] == "session_start"


# -- working_dir / allowed_commands / shell_timeout / mud auto-registration --


def test_working_dir_truthy_registers_file_system_and_shell_tools(tmp_path):
    boukensha.run(task="hello", api_key="sk-test", working_dir=str(tmp_path), mud=False)

    client = FakeClient.instances[0]
    tools = client.builder._context.tools
    assert "pwd" in tools
    assert "read_file" in tools
    assert "run_command" in tools


def test_working_dir_false_registers_neither(tmp_path):
    boukensha.run(task="hello", api_key="sk-test", working_dir=False, mud=False)

    client = FakeClient.instances[0]
    tools = client.builder._context.tools
    assert "pwd" not in tools
    assert "run_command" not in tools


def test_mud_none_and_no_config_registers_no_mud_tools(tmp_path):
    # settings.toml (from isolated_config) has no [mud] section
    boukensha.run(task="hello", api_key="sk-test", working_dir=str(tmp_path))

    client = FakeClient.instances[0]
    tools = client.builder._context.tools
    assert "mud_connect" not in tools


def test_mud_none_with_config_mud_host_and_username_registers_mud_tools(tmp_path, monkeypatch):
    settings_with_mud = (
        '[tasks.player]\nprovider = "anthropic"\nmodel = "claude-haiku-4-5"\n'
        '\n[mud]\nhost = "example.test"\nport = 5000\nusername = "alice"\npassword = "secret"\n'
    )
    (tmp_path / "settings.toml").write_text(settings_with_mud)
    monkeypatch.setattr(boukensha, "_config", None)

    class FakeMudModule:
        registered_with = None

        @staticmethod
        def register(registry, **kwargs):
            FakeMudModule.registered_with = kwargs
            registry.tool("mud_connect", description="fake", parameters={}, block=lambda: "ok")

    monkeypatch.setattr(boukensha.tools, "mud", FakeMudModule)

    boukensha.run(task="hello", api_key="sk-test", working_dir=False)

    assert FakeMudModule.registered_with == {
        "host": "example.test",
        "port": 5000,
        "name": "alice",
        "password": "secret",
    }


def test_mud_false_never_registers_regardless_of_config(tmp_path, monkeypatch):
    settings_with_mud = (
        '[tasks.player]\nprovider = "anthropic"\nmodel = "claude-haiku-4-5"\n'
        '\n[mud]\nhost = "example.test"\nusername = "alice"\npassword = "secret"\n'
    )
    (tmp_path / "settings.toml").write_text(settings_with_mud)
    monkeypatch.setattr(boukensha, "_config", None)

    class FailIfCalled:
        @staticmethod
        def register(registry, **kwargs):
            raise AssertionError("mud.register should not be called when mud=False")

    monkeypatch.setattr(boukensha.tools, "mud", FailIfCalled)

    boukensha.run(task="hello", api_key="sk-test", working_dir=False, mud=False)  # must not raise


def test_explicit_mud_dict_bypasses_config_entirely(tmp_path, monkeypatch):
    class FakeMudModule:
        registered_with = None

        @staticmethod
        def register(registry, **kwargs):
            FakeMudModule.registered_with = kwargs

    monkeypatch.setattr(boukensha.tools, "mud", FakeMudModule)

    explicit = {"host": "explicit.test", "port": 1234, "name": "bob", "password": "pw"}
    boukensha.run(task="hello", api_key="sk-test", working_dir=False, mud=explicit)

    assert FakeMudModule.registered_with == explicit
