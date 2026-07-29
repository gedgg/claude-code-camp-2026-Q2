
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


def test_cwd_boukensha_no_longer_resolved_when_env_unset(tmp_path, monkeypatch):
    # 08_the_repl_loop's cwd-.boukensha resolution tier is reverted in this
    # step (matching Ruby's own history) — a .boukensha/ in the cwd is now
    # ignored; only the env var or the ~/.boukensha default apply.
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)
    project_dir = tmp_path / "project"
    (project_dir / ".boukensha").mkdir(parents=True)
    monkeypatch.chdir(project_dir)

    from boukensha.config import DEFAULT_DIR

    config = Config()
    assert config.dir == DEFAULT_DIR.expanduser().resolve()
    assert config.dir != (project_dir / ".boukensha").resolve()


def test_falls_back_to_home_default_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    from boukensha.config import DEFAULT_DIR

    config = Config()
    assert config.dir == DEFAULT_DIR.expanduser().resolve()


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


def test_mud_accessors_read_from_settings(boukensha_dir):
    # Reappear in this step, matching the Ruby source's own history (removed
    # in 06_the_logger, restored here — nothing in this step actually uses
    # them yet either, but Config's shape now matches Ruby's again).
    config = Config()
    assert config.mud_host == "mud.example.com"
    assert config.mud_port == 4001
    assert config.mud_username == "alice"
    assert config.mud_password == "secret"


def test_mud_accessors_default_when_missing(tmp_path, monkeypatch):
    (tmp_path / "settings.toml").write_text('[tasks.player]\nprovider = "anthropic"\nmodel = "m"\n')
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    config = Config()
    assert config.mud_host == "localhost"
    assert config.mud_port == 4000
    assert config.mud_username is None
    assert config.mud_password is None


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
