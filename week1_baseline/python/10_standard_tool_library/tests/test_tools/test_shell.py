from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.tools import shell


def make_registry(tmp_path, **kwargs):
    ctx = Context()
    registry = Registry(ctx)
    shell.register(registry, working_dir=tmp_path, **kwargs)
    return registry


def test_plain_command_returns_combined_stdout(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.dispatch("run_command", {"command": "echo hello"})
    assert result == "hello"


def test_command_runs_inside_working_directory(tmp_path):
    (tmp_path / "marker.txt").write_text("x")
    registry = make_registry(tmp_path)
    result = registry.dispatch("run_command", {"command": "ls"})
    assert "marker.txt" in result


def test_nonzero_exit_appends_exit_note(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.dispatch("run_command", {"command": "exit 3"})
    assert result == "(no output)\n[exit 3]"


def test_no_output_reports_placeholder(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.dispatch("run_command", {"command": "true"})
    assert result == "(no output)"


def test_allowed_commands_rejects_disallowed_executable_without_running_it(tmp_path):
    registry = make_registry(tmp_path, allowed_commands=["git"])

    result = registry.dispatch("run_command", {"command": "touch should_not_be_created.txt"})

    assert result == "error: 'touch' is not in the allowed-commands list (git)"
    assert not (tmp_path / "should_not_be_created.txt").exists()


def test_allowed_commands_permits_listed_executable(tmp_path):
    registry = make_registry(tmp_path, allowed_commands=["echo"])
    result = registry.dispatch("run_command", {"command": "echo hi"})
    assert result == "hi"


def test_command_times_out(tmp_path):
    registry = make_registry(tmp_path, timeout=1)
    result = registry.dispatch("run_command", {"command": "sleep 5"})
    assert result == "error: command timed out after 1s: sleep 5"


def test_nonexistent_command_reports_error_via_shell_exit_not_exception(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.dispatch("run_command", {"command": "this_command_does_not_exist_xyz"})
    assert "[exit" in result
