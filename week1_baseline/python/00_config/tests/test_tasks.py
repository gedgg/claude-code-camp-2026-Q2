import pytest

from boukensha.errors import ConfigError
from boukensha.tasks.base import Task
from boukensha.tasks.player import Player


def test_task_name():
    assert Player.task_name() == "player"


def test_base_task_name_is_abstract():
    with pytest.raises(NotImplementedError):
        Task.task_name()


def test_provider_and_model_read_from_settings():
    settings = {"provider": "anthropic", "model": "claude-haiku-4-5"}
    assert Player.provider(settings) == "anthropic"
    assert Player.model(settings) == "claude-haiku-4-5"


def test_provider_missing_raises_config_error():
    with pytest.raises(ConfigError, match="tasks.player.provider"):
        Player.provider({"model": "claude-haiku-4-5"})


def test_model_missing_raises_config_error():
    with pytest.raises(ConfigError, match="tasks.player.model"):
        Player.model({"provider": "anthropic"})


def test_prompt_override_defaults_false():
    assert Player.prompt_override({}) is False
    assert Player.prompt_override({"prompt_override": "not-a-dict"}) is False
    assert Player.prompt_override({"prompt_override": {"system": False}}) is False


def test_prompt_override_true_when_set():
    assert Player.prompt_override({"prompt_override": {"system": True}}) is True


def test_system_prompt_uses_default_when_no_override(tmp_path):
    default_dir = tmp_path / "default_prompts"
    default_dir.mkdir()
    (default_dir / "system.md").write_text("default prompt\n")

    text = Player.system_prompt({}, default_prompts_dir=default_dir)
    assert text == "default prompt"


def test_system_prompt_uses_user_override_when_flagged_and_present(tmp_path):
    default_dir = tmp_path / "default_prompts"
    default_dir.mkdir()
    (default_dir / "system.md").write_text("default prompt\n")

    user_dir = tmp_path / "user_prompts"
    (user_dir / "player").mkdir(parents=True)
    (user_dir / "player" / "system.md").write_text("user override prompt\n")

    settings = {"prompt_override": {"system": True}}
    text = Player.system_prompt(settings, user_prompts_dir=user_dir, default_prompts_dir=default_dir)
    assert text == "user override prompt"


def test_system_prompt_falls_back_to_default_when_override_flagged_but_file_missing(tmp_path):
    default_dir = tmp_path / "default_prompts"
    default_dir.mkdir()
    (default_dir / "system.md").write_text("default prompt\n")

    user_dir = tmp_path / "user_prompts"  # exists, but no player/system.md inside

    settings = {"prompt_override": {"system": True}}
    text = Player.system_prompt(settings, user_prompts_dir=user_dir, default_prompts_dir=default_dir)
    assert text == "default prompt"


def test_system_prompt_ignores_user_override_when_not_flagged(tmp_path):
    default_dir = tmp_path / "default_prompts"
    default_dir.mkdir()
    (default_dir / "system.md").write_text("default prompt\n")

    user_dir = tmp_path / "user_prompts"
    (user_dir / "player").mkdir(parents=True)
    (user_dir / "player" / "system.md").write_text("user override prompt\n")

    text = Player.system_prompt({}, user_prompts_dir=user_dir, default_prompts_dir=default_dir)
    assert text == "default prompt"
