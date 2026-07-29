# 04 · The API Client (Python)

Python port of `week1_baseline/ruby/04_api_client`. See
[`docs/plans/python_port/04_api_client`](../../../docs/plans/python_port/04_api_client)
for the full port plan and the decisions behind the differences from Ruby
called out below.

`PromptBuilder`, all five backends, `Registry`, `Tool`, `Message`,
`Context` are unchanged from
[`03_prompt_builder`](../03_prompt_builder/README.md) — copied forward
verbatim. This step adds `Client`: one HTTP POST, one response — still no
tool-calling loop (that's `05_agent_loop`).

## `boukensha.client.Client`

Stdlib-only (`urllib.request`/`json`/`ssl`) — no HTTP library dependency,
same as Ruby's `net/http`-only design. `Client(builder).call(max_output_tokens=1024)`:

1. Builds the request from `builder.url`/`builder.headers`/
   `builder.to_api_payload(...)`.
2. Retries transient network errors and a fixed set of retryable HTTP
   status codes (`408, 409, 429, 500, 502, 503, 504`), up to 3 retries,
   exponential backoff (`0.5s, 1.0s, 2.0s`).
3. Raises `boukensha.errors.ApiError` on final failure — a non-retryable
   status fails immediately (no retries consumed); exhausted retries fail
   with an attempt count in the message.
4. Returns the parsed JSON response body as a plain `dict` on success — no
   interpretation of `stop_reason`/tool calls happens here (that's
   `05_agent_loop`'s job).

## Differences from the Ruby version

- **`urllib.error.HTTPError` is treated as a normal response, not a
  network failure** — Ruby's `Net::HTTP#request` always returns a response
  object, even for a 500; Python's `urlopen` *raises* `HTTPError` for any
  non-2xx status instead. `Client.call` catches it immediately and treats
  it exactly like a non-success response for the retry/`ApiError` logic
  (its `.code`/`.read()` become the status/body), so the *policy* (retry
  if the status is in the retryable set and attempts remain, else fail)
  stays identical to Ruby even though the mechanism differs.
- **Transient-error class mapping** — Ruby's `TRANSIENT_ERRORS` (`EOFError`,
  `Errno::ECONNRESET`, `Errno::ECONNREFUSED`, `Net::OpenTimeout`,
  `Net::ReadTimeout`, `OpenSSL::SSL::SSLError`, `SocketError`,
  `Timeout::Error`) becomes Python's `http.client.RemoteDisconnected`,
  `ConnectionResetError`, `ConnectionRefusedError`, `TimeoutError`,
  `socket.timeout`, `ssl.SSLError`, `urllib.error.URLError` (which wraps
  most low-level socket/DNS/SSL failures `urlopen` raises).
- **No SSL cert-file workaround needed.** Ruby's client has a
  commented-out `ca_file = OpenSSL::X509::DEFAULT_CERT_FILE` line, removed
  because that path doesn't exist on Linux/WSL2. Python's `urllib.request`
  verifies against the system CA store by default, uniformly across
  platforms — nothing to work around here.
- **`Task.provider`/`.model`/`.prompt_override` now guard against a
  non-dict `settings`** (e.g. `None`, when `config.tasks("missing_task")`
  finds nothing) via a private `_setting` helper, so they raise the
  intended `ConfigError`/return `False` instead of `AttributeError` from a
  bare `.get()` call on `None` — a real behavioural fix, ported from
  Ruby's equivalent `settings.is_a?(Hash)` guard in `tasks/base.rb`.
- **`config.py`'s `PROMPTS_DIR` is *not* changed** — Ruby's `config.rb`
  introduces an off-by-one `../` bug in this step that resolves to a
  nonexistent directory (silently masked by `settings.yaml`'s
  `prompt_override.system = true`). The Python port already computed
  `PROMPTS_DIR` correctly back in `02_the_registry` and keeps doing so;
  this Ruby regression is not replicated.

## Code Layout

| File | Purpose |
|------|---------|
| `src/boukensha/{config,tool,message,context,registry,prompt_builder}.py`, `backends/` | Unchanged from `03_prompt_builder` |
| `src/boukensha/tasks/base.py` | `Task`: adds the `_setting` non-dict guard |
| `src/boukensha/client.py` | `Client` |
| `examples/example.py` | Runnable smoke-test — makes a real network call |
| `tests/` | pytest coverage; `test_client.py` mocks `urlopen`, no real network calls |

## Run Example

```bash
./week1_baseline/bin/python/04_api_client
```

This makes a real network call to the configured provider (needs a valid
API key in `.boukensha/.env`).

## Development

```bash
cd week1_baseline/python/04_api_client
uv sync
uv run pytest -v
uv run ruff check src examples tests
```
