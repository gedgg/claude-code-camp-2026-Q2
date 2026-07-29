import builtins

import pytest

import boukensha
from boukensha.context import Context
from boukensha.errors import ApiError, LoopError
from boukensha.repl import Repl


class FakeBackend:
    model = "fake-model"


class FakeBuilder:
    def __init__(self):
        self.backend = FakeBackend()

    def parse_response(self, response):
        return response


class FakeClient:
    def __init__(self, responses=None):
        self._responses = list(responses or [])

    def call(self, **kwargs):
        if not self._responses:
            return {"stop_reason": "end_turn", "content": [{"type": "text", "text": "ok"}]}
        return self._responses.pop(0)


class RaisingClient(FakeClient):
    def __init__(self, exc):
        super().__init__()
        self._exc = exc

    def call(self, **kwargs):
        raise self._exc


class NullLogger:
    def __init__(self):
        self.turns = []

    def turn(self, *, n):
        self.turns.append(n)

    def iteration(self, **kwargs):
        pass

    def limit_reached(self, **kwargs):
        pass

    def turn_end(self, **kwargs):
        pass

    def prompt(self, **kwargs):
        pass

    def tool_call(self, **kwargs):
        pass

    def tool_result(self, **kwargs):
        pass

    def response(self, **kwargs):
        pass

    def raw(self, **kwargs):
        pass


def make_repl(*, client=None, config_dir=None, provider="anthropic", model="m", version="0.8.0", api_key="sk-test"):
    ctx = Context()
    logger = NullLogger()
    repl = Repl(
        context=ctx,
        registry=None,
        builder=FakeBuilder(),
        client=client or FakeClient(),
        logger=logger,
        config_dir=config_dir,
        provider=provider,
        model=model,
        version=version,
        api_key=api_key,
    )
    return repl, ctx, logger


def feed_input(monkeypatch, lines):
    it = iter(lines)

    def fake_input(*args, **kwargs):
        try:
            return next(it)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr(builtins, "input", fake_input)


@pytest.fixture(autouse=True)
def reset_quiet_flag(monkeypatch):
    monkeypatch.setattr(boukensha, "_quiet", False)
    yield
    monkeypatch.setattr(boukensha, "_quiet", False)


def test_plain_input_runs_one_turn_per_line(monkeypatch, capsys):
    repl, ctx, logger = make_repl(client=FakeClient([{"stop_reason": "end_turn", "content": [{"type": "text", "text": "hi there"}]}]))
    feed_input(monkeypatch, ["hello", "/exit"])

    repl.start()

    assert logger.turns == [1]
    out = capsys.readouterr().out
    assert "hi there" in out
    assert "Goodbye." in out
    assert [m.role for m in ctx.messages] == ["user", "assistant"]


def test_exit_and_quit_both_end_the_loop_without_consuming_further_input(monkeypatch, capsys):
    repl, _ctx, logger = make_repl()
    feed_input(monkeypatch, ["/quit", "should not be read"])

    repl.start()

    assert logger.turns == []
    assert "Goodbye." in capsys.readouterr().out


def test_help_prints_static_text_and_is_not_a_turn(monkeypatch, capsys):
    repl, _ctx, logger = make_repl()
    feed_input(monkeypatch, ["/help", "/exit"])

    repl.start()

    assert logger.turns == []
    assert "Commands:" in capsys.readouterr().out


def test_quiet_and_loud_toggle_module_flag_and_are_not_turns(monkeypatch):
    repl, _ctx, logger = make_repl()
    feed_input(monkeypatch, ["/quiet", "/loud", "/exit"])

    repl.start()

    assert logger.turns == []
    assert boukensha.is_quiet() is False  # toggled on then back off


def test_clear_wipes_history_resets_turn_counter_and_is_not_itself_a_turn(monkeypatch):
    repl, ctx, logger = make_repl(
        client=FakeClient(
            [
                {"stop_reason": "end_turn", "content": [{"type": "text", "text": "one"}]},
                {"stop_reason": "end_turn", "content": [{"type": "text", "text": "two"}]},
            ]
        )
    )
    feed_input(monkeypatch, ["first", "/clear", "second", "/exit"])

    repl.start()

    assert logger.turns == [1, 1]  # turn counter reset by /clear
    assert [m.content for m in ctx.messages] == ["second", "two"]


def test_blank_input_line_is_skipped_entirely(monkeypatch):
    repl, _ctx, logger = make_repl()
    feed_input(monkeypatch, ["   ", "/exit"])

    repl.start()

    assert logger.turns == []


def test_eof_ends_loop_silently_without_goodbye_message(monkeypatch, capsys):
    repl, _ctx, _logger = make_repl()
    feed_input(monkeypatch, [])  # immediate EOF

    repl.start()

    assert "Goodbye." not in capsys.readouterr().out


def test_api_error_during_turn_prints_error_and_continues(monkeypatch, capsys):
    repl, _ctx, _logger = make_repl(client=RaisingClient(ApiError("boom")))
    feed_input(monkeypatch, ["hello", "/exit"])

    repl.start()

    out = capsys.readouterr().out
    assert "[error] API call failed: boom" in out
    assert "Goodbye." in out


def test_loop_error_during_turn_prints_error_and_continues(monkeypatch, capsys):
    repl, _ctx, _logger = make_repl(client=RaisingClient(LoopError("runaway")))
    feed_input(monkeypatch, ["hello", "/exit"])

    repl.start()

    out = capsys.readouterr().out
    assert "[error] runaway" in out
    assert "Goodbye." in out


def test_banner_shows_directory_not_found_when_config_dir_missing(tmp_path, monkeypatch):
    repl, _ctx, _logger = make_repl(config_dir=tmp_path / "nonexistent")
    feed_input(monkeypatch, ["/exit"])
    # capture the banner text directly rather than via stdout, for a precise assertion
    banner = repl._banner()
    assert "✗ directory not found" in banner


def test_banner_shows_api_key_not_set_when_blank(tmp_path):
    repl, _ctx, _logger = make_repl(api_key="")
    assert "✗ API key not set" in repl._banner()


def test_banner_shows_api_key_set_when_present():
    repl, _ctx, _logger = make_repl(api_key="sk-real")
    assert "✓ API key set" in repl._banner()
