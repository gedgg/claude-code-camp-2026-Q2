import io
import json
import urllib.error

import pytest

from boukensha.client import Client
from boukensha.errors import ApiError


class FakeBuilder:
    def __init__(self):
        self.url = "https://example.test/api/messages"
        self.headers = {"Content-Type": "application/json", "x-api-key": "sk-test"}
        self.payload_calls = []

    def to_api_payload(self, *, max_output_tokens=1024):
        self.payload_calls.append(max_output_tokens)
        return {"model": "test-model", "max_output_tokens": max_output_tokens}


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(status, body=b""):
    return urllib.error.HTTPError(
        url="https://example.test/api/messages", code=status, msg="err", hdrs=None, fp=io.BytesIO(body)
    )


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr("boukensha.client.time.sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


def test_clean_200_returns_parsed_json(monkeypatch):
    builder = FakeBuilder()
    body = json.dumps({"ok": True}).encode()

    monkeypatch.setattr("boukensha.client.urllib.request.urlopen", lambda req: FakeResponse(200, body))

    result = Client(builder).call()
    assert result == {"ok": True}
    assert builder.payload_calls == [1024]


def test_single_retryable_failure_then_success(monkeypatch, no_real_sleep):
    builder = FakeBuilder()
    body = json.dumps({"ok": True}).encode()
    calls = [http_error(503), None]

    def fake_urlopen(req):
        step = calls.pop(0)
        if step is not None:
            raise step
        return FakeResponse(200, body)

    monkeypatch.setattr("boukensha.client.urllib.request.urlopen", fake_urlopen)

    result = Client(builder).call()
    assert result == {"ok": True}
    assert no_real_sleep == [0.5]


def test_retries_exhausted_on_persistent_retryable_status_raises_api_error(monkeypatch, no_real_sleep):
    builder = FakeBuilder()

    def fake_urlopen(req):
        raise http_error(503, b"still failing")

    monkeypatch.setattr("boukensha.client.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ApiError, match=r"failed after 4 attempts \(503\)"):
        Client(builder).call()

    assert len(no_real_sleep) == 3  # one sleep between each of the 4 attempts, minus the last


def test_non_retryable_status_raises_immediately_after_one_attempt(monkeypatch, no_real_sleep):
    builder = FakeBuilder()
    attempts = []

    def fake_urlopen(req):
        attempts.append(1)
        raise http_error(404, b"not found")

    monkeypatch.setattr("boukensha.client.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ApiError, match=r"failed after 1 attempt \(404\): not found"):
        Client(builder).call()

    assert len(attempts) == 1
    assert no_real_sleep == []


def test_transient_network_exception_retried_then_succeeds(monkeypatch, no_real_sleep):
    builder = FakeBuilder()
    body = json.dumps({"ok": True}).encode()
    calls = [ConnectionResetError("reset"), None]

    def fake_urlopen(req):
        step = calls.pop(0)
        if step is not None:
            raise step
        return FakeResponse(200, body)

    monkeypatch.setattr("boukensha.client.urllib.request.urlopen", fake_urlopen)

    result = Client(builder).call()
    assert result == {"ok": True}


def test_transient_network_exception_exhausting_retries_raises_api_error(monkeypatch, no_real_sleep):
    builder = FakeBuilder()

    def fake_urlopen(req):
        raise ConnectionRefusedError("refused")

    monkeypatch.setattr("boukensha.client.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ApiError, match=r"failed after 4 attempts: ConnectionRefusedError"):
        Client(builder).call()


def test_headers_url_and_body_built_from_prompt_builder(monkeypatch):
    builder = FakeBuilder()
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["body"] = json.loads(req.data)
        return FakeResponse(200, b"{}")

    monkeypatch.setattr("boukensha.client.urllib.request.urlopen", fake_urlopen)

    Client(builder).call(max_output_tokens=256)

    assert captured["url"] == "https://example.test/api/messages"
    assert captured["headers"]["x-api-key"] == "sk-test"
    assert captured["body"] == {"model": "test-model", "max_output_tokens": 256}
