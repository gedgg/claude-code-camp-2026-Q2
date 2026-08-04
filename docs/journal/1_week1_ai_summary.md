# Week 1 Learning Journey — Building BOUKENSHA in Ruby

This week's material (`ruby/00_config` through `ruby/12_context`) is a
13-step guided build of **BOUKENSHA**, a from-scratch LLM agent framework
in Ruby. Each folder is a complete, runnable snapshot of the project at
that stage — nothing is left as an exercise stub, so the sequence doubles
as a reference implementation of "how do you build Claude Code (or any
coding/tool-using agent) yourself, one concept at a time."

The throughline: start with *how do I even structure config and data*,
build up to *a single API call*, then *a working tool-use loop*, then
wrap that loop in progressively more production-grade shells (logging,
a DSL, a REPL, packaging, a standard tool library, a TUI, and finally
context-window management). By step 12 you have a small but real
"Claude Code"-shaped tool: a packaged `boukensha` executable with a
terminal UI, a standard library of file/shell tools, structured
JSONL logging, and automatic context compaction.

---

## The Sequence

### 00 · Configuration
**Concept: don't hardcode what should be configurable.**
Introduces `Boukensha::Config`, which resolves a `.boukensha/` directory
(env var → `~/.boukensha`) holding `.env` (secrets) and `settings.yaml`
(everything else). Configuration is organized **by task** — a named role
in the agent loop bound to its own provider/model — rather than as flat
global settings. Only one task (`player`) exists yet, but this shape is
what lets later steps assign different models to different roles.
Introduces the abstract `Tasks::Base` / concrete `Tasks::Player` split:
stateless classes operating on a settings hash rather than instances.

### 01 · The Struct Skeleton
**Concept: name your core data before you write behavior.**
Defines the three structs everything else is built on:
- `Tool` — name, description, parameters, block (what the agent can call)
- `Message` — role, content, tool_use_id (one turn of conversation)
- `Context` — system prompt, messages, tools, token budget (everything
  needed to make one API call, and nothing else)

Uses plain Ruby `Struct`s deliberately for readability over "proper"
classes — a teaching-code tradeoff called out explicitly in the README.

### 02 · The Registry
**Concept: the agent never executes code directly — it asks for it.**
`Boukensha::Registry` stores tools and dispatches calls by name. The
model only ever emits a structured `{name, args}` request; the Registry
looks up the block and runs it. Introduces `UnknownToolError` as an
explicit error boundary (no silent failure on a hallucinated tool name),
and highlights a real gotcha: string keys from parsed API JSON must be
converted to symbol keys before calling a Ruby block.

### 03 · The Prompt Builder
**Concept: one internal `Context`, many wire formats.**
Because provider APIs disagree about nearly everything — where the
system prompt goes, how tool results are wrapped, what a tool schema
looks like, even what the assistant's role is called (`assistant` vs.
`model`) — `PromptBuilder` delegates serialization to a per-provider
`Backend` (Anthropic, OpenAI, Gemini, Ollama, Ollama Cloud). This is the
adapter-pattern lesson: keep one canonical internal representation and
push all provider-specific quirks to the edges. Backends also own their
supported-model tables (context window, token pricing, usage unit) and
refuse to construct with an unrecognized model — config typos fail fast
instead of hitting the API with garbage.

### 04 · The API Client
**Concept: prove the wire round-trip before adding a loop around it.**
`Boukensha::Client` takes the payload from `PromptBuilder` and does one
HTTP POST via Ruby's stdlib `net/http` — deliberately no HTTP gem, so the
request/response mechanics stay visible. Adds `ApiError` for non-2xx
responses (explicit failure over a confusing nil). This step is a single
call/response with no tool dispatch yet — just confirming that config →
prompt building → HTTP all connect correctly before adding the loop.

### 05 · The Agent Loop
**Concept: this is the actual agent.**
Everything before this was scaffolding. `Boukensha::Agent#run` is the
loop: send messages → check `stop_reason` → if `"tool_use"`, dispatch
each requested tool via the Registry, inject results as `tool_result`
messages, and go around again; if `"end_turn"`, return the final text.
The key generalizing idea introduced here: every backend implements
`parse_response`, normalizing five very different provider response
shapes into one common `{stop_reason, content}` shape, so the Agent loop
itself never touches a raw provider response. Also introduces
`max_iterations` as a turn ceiling (so a misbehaving agent can't loop
forever) and documents an Anthropic-specific ordering constraint: the
assistant's tool_use message must be recorded before its tool_result or
the API rejects the request.

### 06 · The Logger
**Concept: observability is not optional in an agent harness.**
`Boukensha::Logger` writes one JSON-Lines file per session under
`.boukensha/sessions/<session-id>.jsonl` — structured, grep/tail-friendly
events (`session_start`, `iteration`, `prompt`, `tool_call`,
`tool_result`, `response`, `raw`). Response events record task, provider,
model, token counts, and estimated USD cost using the backend's pricing
metadata from step 03. `Boukensha.debug!` opts into logging raw provider
payloads. This is the "you can't fix what you can't see" step — every
later step (REPL, TUI) is built on top of these log events.

### 07 · The `Boukensha.run` DSL
**Concept: hide plumbing behind a small, intentional surface.**
Every prior step required manually wiring `Context`, `Registry`,
`Backend`, `PromptBuilder`, `Client`, `Logger`, and `Agent` by hand
(~20 lines). `Boukensha.run(task:, ...) { tool "..." }` collapses all of
that into one call plus a block, using `instance_eval` against a tiny
`RunDSL` host object that exposes exactly one method (`tool`) — a
deliberate restriction so callers can't reach internal state. This is
the "hello world" entry point the rest of the framework builds on.

### 08 · The REPL Loop
**Concept: from one-shot task to a persistent conversation.**
`Boukensha.repl` turns the single-turn DSL into a multi-turn interactive
session with built-in commands (`/quiet`, `/loud`, `/clear`, `/help`,
`/exit`). Requires two underlying changes: `Context#clear_messages!` (wipe
history, keep tools registered) and — more subtly — the Agent must now
persist its final reply into the context (previously discarded after a
one-shot run) so later turns can see the prior exchange. Demonstrates
this concretely: asking "what was the first file I asked about?" only
works because history now accumulates.

### 09 · Global Executable
**Concept: ship it as a real tool, not a script you `cd` into.**
Packages BOUKENSHA as a gem (`boukensha.gemspec`, `bin/boukensha`) so the
`boukensha` command works from anywhere on the machine. Introduces
`boukensha_loader.rb`, which resolves *which step's lib* to boot
(`BOUKENSHA_PATH` env var → `~/.boukensharc` file → bundled default) —
notably, the gem doesn't copy code from the step folders, it just knows
where to find them, keeping the numbered teaching folders as the single
source of truth even after packaging.

### 10 · A Standard Tool Library
**Concept: a real harness ships capabilities, not just a mechanism for capabilities.**
Adds two built-in tool modules, auto-registered when `working_dir:` is
set: `Tools::FileSystem` (`pwd`, `list_directory`, `read_file`,
`write_file`, `delete_file`, `search_files`) and `Tools::Shell`
(`run_command`). Two security-relevant constraints are load-bearing here:
filesystem tools reject absolute paths and `..` traversal outside the
working directory, and shell commands run under a configurable timeout
with an optional command allow-list (`allowed_commands: ["ruby", "git"]`)
— `nil` allows everything, an explicit list locks the agent down. This
is the sandboxing lesson: giving an LLM real file/shell access requires
deliberate boundaries, not just capability.

### 11 · A Terminal UI
**Concept: separate the interaction loop from its I/O.**
Adds `Boukensha::Tui`, a four-zone terminal UI (scrollable conversation,
live progress line, input box, always-on status line) built on the
`charm` gem (bubbletea/lipgloss/bubbles). The enabling refactor is in
`Repl`: raw `puts`/`gets` are replaced with `on_output(&block)`,
`handle_command`, and `run_turn` as public seams, so `Tui` (or any other
front-end) can drive the same REPL logic without owning I/O directly.
`Logger#subscribe` complements this — every structured log event is now
broadcast to subscribers in addition to being written to disk, which is
how the TUI updates its live progress line (spinner, iteration count,
token counts, elapsed time) without polling. The agent runs on a
background thread so the UI stays responsive mid-turn, and `tui: false`
/ `--no-tui` preserves the plain REPL as a fallback.

### 12 · Context Management
**Concept: you own the context window; nothing compacts it for you.**
Final step. Fixes a real bug from earlier steps — the displayed "usage"
was actually the *output* token budget and a cumulative sum that never
reset, not the true input context size. `Context` now tracks
`context_window` (model capacity) separately from `current_tokens`
(actual input tokens from the last response), updated after every API
call including mid-turn tool-use round-trips. Adds color-coded usage
indicators (grey/yellow/red at 70%/85% thresholds) and **auto-compaction**:
at ≥85% usage, the Agent drops the oldest ~40% of messages (keeping at
least 2) before the next call, with a manual `/compact` command and a
`Logger#compaction` event for observability. This closes the loop opened
in step 06 (logging) and step 11 (TUI subscriptions) — compaction is
just another event the UI reacts to.

---

## What This Journey Actually Teaches

Read top to bottom, the 13 steps form a deliberate arc through the same
problems any real agent framework (including Claude Code itself) has to
solve, in dependency order:

1. **Config & data modeling** (00–01) before any behavior exists.
2. **Isolate the two real "opaque box" boundaries** — invoking a tool
   (02, Registry) and invoking a model (03–04, Backend/Client) — behind
   narrow interfaces before combining them.
3. **The loop itself** (05) is small once the boundaries are clean:
   normalize provider responses to one shape and the control flow is a
   single branch.
4. **Production concerns layer on without touching the loop's core**:
   observability (06), ergonomics (07), statefulness (08), distribution
   (09), capability (10), presentation (11), and resource management (12)
   are each additive — none of them required rewriting the Agent loop
   from step 05.
5. **Multi-provider support is a recurring tax**, paid once at the
   Backend layer (03) and amortized everywhere else — a concrete
   demonstration of why the adapter pattern earns its complexity when
   you truly need to support 5 incompatible APIs.
6. **Safety boundaries are explicit, not implicit** — unknown tool names
   raise, unsupported models refuse to construct, filesystem access is
   sandboxed to a working directory, shell commands can be allow-listed,
   and runaway loops have an iteration ceiling. None of these guardrails
   were bolted on generically; each was added at the exact step where
   its risk first became real (dispatch → model config → real file
   access → real shell access → runaway generation).

By the end, `12_context` is a small but genuine coding-agent harness:
config-driven, multi-provider, tool-using, logged, REPL/TUI-driven,
packaged as a global executable, with a standard tool library and
context-window management — essentially a miniature, from-first-principles
version of the tools this course is being written *in*.
