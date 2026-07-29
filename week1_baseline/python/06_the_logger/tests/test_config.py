
import pytest

from boukensha.config import Config

SETTINGS_TOML = """
[tasks.player]
provider = "anthropic"
model = "claude-haiku-4-5"

[tasks.player.prompt_override]
system = true

[mud]
host = "mud.example.com"
port = 4001
username = "alice"
password = "secret"
"""


@pytest.fixture
def boukensha_dir(tmp_path, monkeypatch):
    (tmp_path / "settings.toml").write_text(SETTINGS_TOML)
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))
    return tmp_path


def test_resolves_dir_from_env(boukensha_dir):
    config = Config()
    assert config.dir == boukensha_dir.resolve()


def test_tasks_with_no_name_returns_full_table(boukensha_dir):
    config = Config()
    assert config.tasks() == {
        "player": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "prompt_override": {"system": True},
        }
    }


def test_tasks_with_name_returns_that_tasks_settings(boukensha_dir):
    config = Config()
    player = config.tasks("player")
    assert player["provider"] == "anthropic"
    assert player["model"] == "claude-haiku-4-5"


def test_tasks_with_unknown_name_returns_none(boukensha_dir):
    config = Config()
    assert config.tasks("nonexistent") is None


def test_mud_accessors_absent_this_step(boukensha_dir):
    # mud_host/mud_port/mud_username/mud_password are dropped in this step
    # (nothing in 05_agent_loop/06_the_logger uses them — they reappear in
    # 07_the_run_dsl, matching the Ruby source's own history).
    config = Config()
    assert not hasattr(config, "mud_host")
    assert not hasattr(config, "mud_port")
    assert not hasattr(config, "mud_username")
    assert not hasattr(config, "mud_password")


def test_missing_settings_file_yields_empty_config(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    config = Config()
    assert config.tasks() == {}


def test_dig_traverses_nested_keys(boukensha_dir):
    config = Config()
    assert config.dig("mud", "host") == "mud.example.com"
    assert config.dig("mud", "missing") is None
    assert config.dig("nonexistent", "key") is None


def test_user_prompts_dir_is_under_config_dir(boukensha_dir):
    config = Config()
    assert config.user_prompts_dir == boukensha_dir / "prompts"


def test_repr_lists_dir_and_tasks(boukensha_dir):
    config = Config()
    text = repr(config)
    assert str(config.dir) in text
    assert "player" in text
