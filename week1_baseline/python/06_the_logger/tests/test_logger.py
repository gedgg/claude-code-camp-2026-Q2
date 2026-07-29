import json

import pytest

from boukensha.logger import Logger


class FakeBackend:
    model = "fake-model"
    usage_unit = "tokens"

    def estimate_cost(self, *, input_tokens, output_tokens):
        return (input_tokens + output_tokens) / 1_000_000.0


class FakeTask:
    @staticmethod
    def task_name():
        return "player"


class FakeMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content


def read_lines(logger):
    return [json.loads(line) for line in logger.path.read_text().splitlines()]


@pytest.fixture(autouse=True)
def isolate_debug_flag(monkeypatch):
    import boukensha

    monkeypatch.setattr(boukensha, "_debug", False)
    yield
    monkeypatch.setattr(boukensha, "_debug", False)


def test_session_start_written_immediately_with_snapshot(tmp_path):
    logger = Logger(dir=tmp_path, snapshot={"task": "player", "model": "x"})
    logger.close()

    lines = read_lines(logger)
    assert len(lines) == 1
    assert lines[0]["phase"] == "session_start"
    assert lines[0]["task"] == "player"
    assert lines[0]["model"] == "x"
    assert lines[0]["session_id"] == logger.session_id
    assert "at" in lines[0]


def test_each_phase_method_writes_one_line(tmp_path):
    logger = Logger(dir=tmp_path)
    logger.iteration(n=1, max=25)
    logger.limit_reached(kind="max_iterations", n=25, max=25)
    logger.turn_end(reason="completed", iterations=3)
    logger.prompt(messages=[FakeMessage("user", "hi")], tools={})
    logger.tool_call(name="move", args={"direction": "north"})
    logger.tool_result(name="move", result="ok")
    logger.response(text="hi there")
    logger.close()

    lines = read_lines(logger)
    phases = [line["phase"] for line in lines]
    assert phases == [
        "session_start",
        "iteration",
        "limit_reached",
        "turn_end",
        "prompt",
        "tool_call",
        "tool_result",
        "response",
    ]

    prompt_line = lines[phases.index("prompt")]
    assert prompt_line["message_count"] == 1
    assert prompt_line["messages"] == [{"role": "user", "content": "hi"}]
    assert prompt_line["tool_count"] == 0
    assert prompt_line["tools"] == []


def test_raw_writes_nothing_when_debug_is_off(tmp_path):
    logger = Logger(dir=tmp_path)
    logger.raw(data={"secret": "response"})
    logger.close()

    lines = read_lines(logger)
    assert [line["phase"] for line in lines] == ["session_start"]


def test_raw_writes_when_debug_is_on(tmp_path):
    import boukensha

    boukensha.debug()
    logger = Logger(dir=tmp_path)
    logger.raw(data={"secret": "response"})
    logger.close()

    lines = read_lines(logger)
    assert [line["phase"] for line in lines] == ["session_start", "raw"]
    assert lines[1]["data"] == {"secret": "response"}


def test_response_computes_execution_metadata_from_backend():
    logger = Logger.__new__(Logger)  # avoid touching disk for this pure-computation test
    logger.session_id = "test"
    metadata = logger._execution_metadata(
        task=FakeTask,
        backend=FakeBackend(),
        usage={"input_tokens": 100, "output_tokens": 50},
    )

    assert metadata["task"] == "player"
    assert metadata["provider"] == "fake_backend"
    assert metadata["model"] == "fake-model"
    assert metadata["usage_unit"] == "tokens"
    assert metadata["input_tokens"] == 100
    assert metadata["output_tokens"] == 50
    assert metadata["cost_usd"] == pytest.approx(0.00015)


def test_execution_metadata_omits_cost_when_backend_lacks_estimate_cost():
    class NoEstimate:
        model = "m"

    logger = Logger.__new__(Logger)
    metadata = logger._execution_metadata(task=None, backend=NoEstimate(), usage={"input_tokens": 1, "output_tokens": 1})
    assert "cost_usd" not in metadata


def test_execution_metadata_empty_when_nothing_given():
    logger = Logger.__new__(Logger)
    assert logger._execution_metadata(task=None, backend=None, usage=None) == {}


def test_response_event_drops_none_metadata_keys_but_keeps_top_level_nulls(tmp_path):
    logger = Logger(dir=tmp_path)
    logger.response(text="hi")  # no usage/stop_reason/task/backend given
    logger.close()

    lines = read_lines(logger)
    response_line = lines[-1]
    assert response_line["phase"] == "response"
    assert response_line["usage"] is None
    assert response_line["stop_reason"] is None
    assert "task" not in response_line
    assert "cost_usd" not in response_line


def test_subscribe_receives_every_event_written_after_it_subscribes(tmp_path):
    # subscribe() is called after construction, so it only sees events
    # written from that point on — session_start (written during __init__,
    # before any subscriber could exist) is not retroactively delivered.
    received = []
    logger = Logger(dir=tmp_path)
    logger.subscribe(received.append)

    logger.iteration(n=1, max=25)
    logger.turn_end(reason="completed", iterations=1)
    logger.close()

    assert [e["phase"] for e in received] == ["iteration", "turn_end"]


def test_close_is_idempotent_safe(tmp_path):
    logger = Logger(dir=tmp_path)
    logger.close()
    logger.close()  # must not raise
