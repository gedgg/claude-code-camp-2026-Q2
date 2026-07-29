from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.tools import file_system


def make_registry(tmp_path):
    ctx = Context()
    registry = Registry(ctx)
    file_system.register(registry, working_dir=tmp_path)
    return registry


def test_pwd_returns_the_root(tmp_path):
    registry = make_registry(tmp_path)
    assert registry.dispatch("pwd") == str(tmp_path.resolve())


def test_list_directory_defaults_to_root_sorted_with_dir_suffix(tmp_path):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()

    registry = make_registry(tmp_path)
    result = registry.dispatch("list_directory")

    assert result == "a.txt\nb.txt\nsub/"


def test_list_directory_empty_dir_reports_empty(tmp_path):
    registry = make_registry(tmp_path)
    assert registry.dispatch("list_directory") == "(empty)"


def test_list_directory_not_a_directory_returns_error_string(tmp_path):
    (tmp_path / "file.txt").write_text("hi")
    registry = make_registry(tmp_path)
    result = registry.dispatch("list_directory", {"path": "file.txt"})
    assert result == "error: 'file.txt' is not a directory"


def test_read_write_delete_round_trip(tmp_path):
    registry = make_registry(tmp_path)

    write_result = registry.dispatch("write_file", {"path": "notes.txt", "content": "hello"})
    assert write_result == "ok: wrote 5 bytes to notes.txt"
    assert registry.dispatch("read_file", {"path": "notes.txt"}) == "hello"

    delete_result = registry.dispatch("delete_file", {"path": "notes.txt"})
    assert delete_result == "ok: deleted notes.txt"
    assert not (tmp_path / "notes.txt").exists()


def test_write_file_creates_missing_parent_directories(tmp_path):
    registry = make_registry(tmp_path)
    registry.dispatch("write_file", {"path": "a/b/c.txt", "content": "x"})
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "x"


def test_read_file_missing_returns_error_not_exception(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.dispatch("read_file", {"path": "missing.txt"})
    assert result == "error: 'missing.txt' is not a file"


def test_delete_file_on_directory_returns_error(tmp_path):
    (tmp_path / "adir").mkdir()
    registry = make_registry(tmp_path)
    result = registry.dispatch("delete_file", {"path": "adir"})
    assert result == "error: 'adir' is not a file"


def test_every_tool_rejects_path_traversal_escaping_root(tmp_path):
    registry = make_registry(tmp_path)

    assert registry.dispatch("read_file", {"path": "../outside.txt"}) == "error: path '../outside.txt' escapes the working directory"
    assert registry.dispatch("list_directory", {"path": ".."}).startswith("error: path '..' escapes")
    assert registry.dispatch("write_file", {"path": "../x.txt", "content": "x"}).startswith("error:")
    assert registry.dispatch("delete_file", {"path": "../x.txt"}).startswith("error:")


def test_search_files_literal_pattern_across_tree(tmp_path):
    (tmp_path / "a.py").write_text("def foo():\n    return 1\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("def bar():\n    return foo()\n")

    registry = make_registry(tmp_path)
    result = registry.dispatch("search_files", {"pattern": "foo"})

    lines = sorted(result.splitlines())
    assert lines == ["a.py:1:def foo():", "sub/b.py:2:    return foo()"]


def test_search_files_glob_filters_which_files_are_searched(tmp_path):
    (tmp_path / "a.py").write_text("needle\n")
    (tmp_path / "a.txt").write_text("needle\n")

    registry = make_registry(tmp_path)
    result = registry.dispatch("search_files", {"pattern": "needle", "glob": "*.py"})

    assert result == "a.py:1:needle"


def test_search_files_no_matches(tmp_path):
    (tmp_path / "a.py").write_text("nothing here\n")
    registry = make_registry(tmp_path)
    assert registry.dispatch("search_files", {"pattern": "zzz_not_present"}) == "no matches"


def test_search_files_invalid_regex_returns_error_string(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.dispatch("search_files", {"pattern": "("})
    assert result.startswith("error: invalid pattern:")


def test_search_files_regex_pattern(tmp_path):
    (tmp_path / "a.py").write_text("value = 123\nvalue = abc\n")
    registry = make_registry(tmp_path)
    result = registry.dispatch("search_files", {"pattern": r"\d+"})
    assert result == "a.py:1:value = 123"
