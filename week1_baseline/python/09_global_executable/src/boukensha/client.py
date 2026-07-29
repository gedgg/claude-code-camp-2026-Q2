from __future__ import annotations

import http.client
import json
import socket
import ssl
import time
import urllib.error
import urllib.request

from boukensha.errors import ApiError

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
TRANSIENT_ERRORS = (
    http.client.RemoteDisconnected,
    ConnectionResetError,
    ConnectionRefusedError,
    TimeoutError,
    socket.timeout,
    ssl.SSLError,
    urllib.error.URLError,
)
MAX_RETRIES = 3
BASE_RETRY_DELAY = 0.5


class Client:
    def __init__(self, builder) -> None:
        self._builder = builder

    def call(self, *, max_output_tokens: int = 1024, tools: list | None = None) -> dict:
        url = self._builder.url
        headers = self._builder.headers
        payload = self._builder.to_api_payload(max_output_tokens=max_output_tokens, tools=tools)
        body = json.dumps(payload).encode()
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")

        attempts = 0
        status: int | None = None
        response_body: bytes = b""

        while True:
            attempts += 1

            try:
                with urllib.request.urlopen(request) as resp:
                    status = resp.status
                    response_body = resp.read()
            except urllib.error.HTTPError as e:
                status = e.code
                response_body = e.read()
            except TRANSIENT_ERRORS as e:
                if attempts > MAX_RETRIES:
                    raise ApiError(f"API request failed after {attempts} attempts: {type(e).__name__}: {e}") from e

                time.sleep(self._retry_delay(attempts))
                continue

            if self._retryable_response(status) and attempts <= MAX_RETRIES:
                time.sleep(self._retry_delay(attempts))
                continue

            break

        if not (200 <= status < 300):
            if status == 401:
                raise ApiError("authentication failed (401) — check your API key")
            attempt_word = "attempt" if attempts == 1 else "attempts"
            raise ApiError(f"API request failed after {attempts} {attempt_word} ({status}): {response_body.decode(errors='replace')}")

        return json.loads(response_body)

    @staticmethod
    def _retryable_response(status: int) -> bool:
        return status in RETRYABLE_STATUS_CODES

    @staticmethod
    def _retry_delay(attempt: int) -> float:
        return BASE_RETRY_DELAY * (2 ** (attempt - 1))
