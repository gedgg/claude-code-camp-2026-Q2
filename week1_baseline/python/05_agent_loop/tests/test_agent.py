import pytest

from boukensha.agent import Agent
from boukensha.context import Context
from boukensha.errors import ApiError


class FakeBuilder:
    """parse_response is the identity function — tests hand Client.call
    canned responses that are already in the normalized {stop_reason,
    content} shape, so there's nothing for a real backend to translate."""

    def parse_response(self, response):
        return response


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("FakeClient.call invoked more times than responses were queued")
        return self._responses.pop(0)


class FakeRegistry:
    def __init__(self, results=None):
        self._results = results or {}
        self.dispatch_calls = []

    def dispatch(self, name, args):
        self.dispatch_calls.append((name, args))
        return self._results.get(name, "ok")


class TaskWithLimits:
    @staticmethod
    def max_iterations(settings):
        return settings.get("max_iterations", 25)

    @staticmethod
    def max_output_tokens(settings):
        return settings.get("max_output_tokens")


class TaskWithoutLimits:
    pass


def make_agent(*, responses, task=TaskWithLimits, task_settings=None, results=None, **kwargs):
    ctx = Context(task=task)
    registry = FakeRegistry(results=results)
    builder = FakeBuilder()
    client = FakeClient(responses)
    agent = Agent(context=ctx, registry=registry, builder=builder, client=client, task_settings=task_settings, **kwargs)
    return agent, ctx, registry, client


def text_response(text):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}


def tool_use_response(*calls):
    content = [
        {"type": "tool_use", "id": call_id, "name": name, "input": args} for call_id, name, args in calls
    ]
    return {"stop_reason": "tool_use", "content": content}


def test_two_iteration_run_dispatches_tool_then_returns_final_text():
    agent, ctx, registry, _client = make_agent(
        responses=[
            tool_use_response(("toolu_1", "move", {"direction": "north"})),
            text_response("You arrive at a corridor."),
        ],
        results={"move": "a torch-lit corridor"},
    )

    result = agent.run()

    assert result == "You arrive at a corridor."
    assert registry.dispatch_calls == [("move", {"direction": "north"})]

    # message ordering: assistant (raw tool_use content) before tool_result
    roles = [m.role for m in ctx.messages]
    assert roles == ["assistant", "tool_result"]
    assert ctx.messages[0].content == tool_use_response(("toolu_1", "move", {"direction": "north"}))["content"]
    assert ctx.messages[1].content == "a torch-lit corridor"
    assert ctx.messages[1].tool_use_id == "toolu_1"


def test_multiple_tool_calls_in_one_response_all_dispatched_before_next_call():
    agent, _ctx, registry, client = make_agent(
        responses=[
            tool_use_response(
                ("toolu_1", "look", {}),
                ("toolu_2", "move", {"direction": "north"}),
            ),
            text_response("done"),
        ],
        results={"look": "a room", "move": "moved"},
    )

    result = agent.run()

    assert result == "done"
    assert registry.dispatch_calls == [("look", {}), ("move", {"direction": "north"})]
    assert len(client.calls) == 2  # both tool calls dispatched within one iteration, no extra client call


def test_iteration_ceiling_reached_triggers_wrap_up():
    agent, ctx, _registry, client = make_agent(
        responses=[
            tool_use_response(("t1", "look", {})),  # consumed as the one counted iteration
            text_response("Summary of progress."),  # consumed as the wrap-up call — ceiling is hit before a 2nd normal iteration
        ],
        results={"look": "a room"},
        max_iterations=1,
    )

    result = agent.run()

    assert result == "Summary of progress."
    # exactly 2 client calls: the one counted iteration + the wrap-up call
    assert len(client.calls) == 2
    assert client.calls[1] == {"tools": [], "max_output_tokens": Agent.WRAP_UP_OUTPUT_TOKENS}
    # the wrap-up directive was injected as an extra user message; the final
    # wrap-up reply itself is returned but not persisted to context (matching
    # 05_agent_loop's Ruby source — that only starts happening in 08_the_repl_loop)
    assert ctx.messages[-1].role == "user"
    assert ctx.messages[-1].content == Agent.WRAP_UP_DIRECTIVE


def test_ceiling_of_zero_disables_the_limit():
    agent, _ctx, _registry, client = make_agent(
        responses=[
            tool_use_response(("t1", "look", {})),
            tool_use_response(("t2", "look", {})),
            tool_use_response(("t3", "look", {})),
            text_response("finally done"),
        ],
        results={"look": "a room"},
        max_iterations=0,
    )

    result = agent.run()

    assert result == "finally done"
    assert len(client.calls) == 4


def test_wrap_up_falls_back_to_deterministic_message_on_api_error():
    class RaisingOnWrapUpClient(FakeClient):
        def call(self, **kwargs):
            if kwargs.get("tools") == []:
                raise ApiError("boom")
            return super().call(**kwargs)

    ctx = Context(task=TaskWithLimits)
    registry = FakeRegistry()
    builder = FakeBuilder()
    client = RaisingOnWrapUpClient([])
    agent = Agent(context=ctx, registry=registry, builder=builder, client=client, max_iterations=0)
    # Force the ceiling to trigger immediately without needing any responses.
    agent._max_iterations = 1
    agent._iteration = 1

    result = agent.run()

    assert "1-action limit" in result
    assert "max_iterations" in result


def test_wrap_up_falls_back_when_text_is_blank():
    ctx = Context(task=TaskWithLimits)
    registry = FakeRegistry()
    builder = FakeBuilder()
    client = FakeClient([text_response("   ")])
    agent = Agent(context=ctx, registry=registry, builder=builder, client=client, max_iterations=1)
    agent._iteration = 1

    result = agent.run()

    assert "1-action limit" in result


def test_explicit_max_iterations_and_max_output_tokens_override_task_settings():
    agent, _ctx, _registry, client = make_agent(
        responses=[text_response("done")],
        task_settings={"max_iterations": 5, "max_output_tokens": 500},
        max_iterations=2,
        max_output_tokens=999,
    )

    agent.run()

    assert agent._max_iterations == 2
    assert client.calls[0] == {"max_output_tokens": 999}


def test_task_settings_without_explicit_args_uses_task_class_values():
    agent, _ctx, _registry, client = make_agent(
        responses=[text_response("done")],
        task_settings={"max_iterations": 7, "max_output_tokens": 321},
    )

    agent.run()

    assert agent._max_iterations == 7
    assert client.calls[0] == {"max_output_tokens": 321}


def test_no_task_settings_and_task_without_max_iterations_uses_agent_default():
    agent, _ctx, _registry, client = make_agent(
        responses=[text_response("done")],
        task=TaskWithoutLimits,
        task_settings=None,
    )

    agent.run()

    assert agent._max_iterations == Agent.MAX_ITERATIONS
    assert client.calls[0] == {}


def test_call_opts_omits_max_output_tokens_key_when_none():
    agent, _ctx, _registry, client = make_agent(
        responses=[text_response("done")],
        task=TaskWithoutLimits,
        task_settings=None,
    )

    agent.run()

    assert "max_output_tokens" not in client.calls[0]


@pytest.mark.parametrize("bad_value", ["not-a-number"])
def test_resolve_max_iterations_int_coercion_raises_on_bad_string(bad_value):
    ctx = Context(task=TaskWithLimits)
    with pytest.raises(ValueError):
        Agent(
            context=ctx,
            registry=FakeRegistry(),
            builder=FakeBuilder(),
            client=FakeClient([]),
            max_iterations=bad_value,
        )
