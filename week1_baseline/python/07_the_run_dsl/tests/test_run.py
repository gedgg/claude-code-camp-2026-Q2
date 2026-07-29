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
