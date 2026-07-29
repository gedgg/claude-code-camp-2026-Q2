import sys

import pytest

import boukensha_loader


@pytest.fixture(autouse=True)
def preserve_boukensha_module():
    """load_and_start_repl() registers a (possibly fixture) module under
    sys.modules["boukensha"]. Save and restore the real package + its
    submodules around every test so other test files' `import boukensha`
    keep seeing the genuine package, not a leftover fixture."""
    saved = {name: mod for name, mod in sys.modules.items() if name == "boukensha" or name.startswith("boukensha.")}
    yield
    for name in list(sys.modules):
        if name == "boukensha" or name.startswith("boukensha."):
            del sys.modules[name]
    sys.modules.update(saved)


def make_fixture_step(tmp_path, name="fixture_step", *, with_repl):
    step_dir = tmp_path / name
    pkg_dir = step_dir / "src" / "boukensha"
    pkg_dir.mkdir(parents=True)
    if with_repl:
        (pkg_dir / "__init__.py").write_text("def repl():\n    return 'fixture repl ran'\n")
    else:
        (pkg_dir / "__init__.py").write_text("# no repl defined in this fixture step\n")
    return step_dir


def test_no_env_var_no_rc_file_resolves_to_bundled_default(monkeypatch, tmp_path):
    monkeypatch.delenv("BOUKENSHA_PATH", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # no ~/.boukensharc here

    assert boukensha_loader.resolve() == boukensha_loader.BUNDLED_LIB


def test_boukensha_path_set_to_valid_step_resolves_to_that_step(monkeypatch, tmp_path):
    step_dir = make_fixture_step(tmp_path, with_repl=True)
    monkeypatch.setenv("BOUKENSHA_PATH", str(step_dir))

    resolved = boukensha_loader.resolve()

    assert resolved == step_dir / "src" / "boukensha" / "__init__.py"
    assert resolved != boukensha_loader.BUNDLED_LIB


def test_boukensha_path_set_to_invalid_dir_aborts_without_falling_through(monkeypatch, tmp_path):
    monkeypatch.setenv("BOUKENSHA_PATH", str(tmp_path / "does_not_exist"))

    with pytest.raises(SystemExit) as exc_info:
        boukensha_loader.resolve()

    assert "does_not_exist" in str(exc_info.value)
    assert "BOUKENSHA_PATH" in str(exc_info.value)


def test_rc_file_pointing_to_valid_step_resolves_to_that_step(monkeypatch, tmp_path):
    monkeypatch.delenv("BOUKENSHA_PATH", raising=False)
    step_dir = make_fixture_step(tmp_path, with_repl=True)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".boukensharc").write_text(str(step_dir) + "\n")
    monkeypatch.setenv("HOME", str(home))

    resolved = boukensha_loader.resolve()

    assert resolved == step_dir / "src" / "boukensha" / "__init__.py"


def test_empty_rc_file_falls_through_to_bundled_default(monkeypatch, tmp_path):
    monkeypatch.delenv("BOUKENSHA_PATH", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".boukensharc").write_text("   \n")
    monkeypatch.setenv("HOME", str(home))

    assert boukensha_loader.resolve() == boukensha_loader.BUNDLED_LIB


def test_rc_file_pointing_to_invalid_path_aborts_without_falling_through(monkeypatch, tmp_path):
    monkeypatch.delenv("BOUKENSHA_PATH", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".boukensharc").write_text(str(tmp_path / "nonexistent_step") + "\n")
    monkeypatch.setenv("HOME", str(home))

    with pytest.raises(SystemExit) as exc_info:
        boukensha_loader.resolve()

    assert ".boukensharc" in str(exc_info.value)


def test_load_and_start_repl_calls_repl_on_resolved_module(monkeypatch, tmp_path):
    step_dir = make_fixture_step(tmp_path, with_repl=True)
    monkeypatch.setenv("BOUKENSHA_PATH", str(step_dir))

    boukensha_loader.load_and_start_repl()  # must not raise


def test_resolved_module_without_repl_attribute_aborts_with_specific_message(monkeypatch, tmp_path):
    step_dir = make_fixture_step(tmp_path, with_repl=False)
    monkeypatch.setenv("BOUKENSHA_PATH", str(step_dir))

    with pytest.raises(SystemExit) as exc_info:
        boukensha_loader.load_and_start_repl()

    message = str(exc_info.value)
    assert "does not support the interactive REPL" in message
    assert str(step_dir) in message


def test_boukensha_debug_prints_loading_from_line(monkeypatch, tmp_path, capsys):
    step_dir = make_fixture_step(tmp_path, with_repl=True)
    monkeypatch.setenv("BOUKENSHA_PATH", str(step_dir))
    monkeypatch.setenv("BOUKENSHA_DEBUG", "1")

    boukensha_loader.load_and_start_repl()

    assert f"loading from: {step_dir}" in capsys.readouterr().out


def test_boukensha_debug_unset_prints_nothing(monkeypatch, tmp_path, capsys):
    step_dir = make_fixture_step(tmp_path, with_repl=True)
    monkeypatch.setenv("BOUKENSHA_PATH", str(step_dir))
    monkeypatch.delenv("BOUKENSHA_DEBUG", raising=False)

    boukensha_loader.load_and_start_repl()

    assert "loading from" not in capsys.readouterr().out
