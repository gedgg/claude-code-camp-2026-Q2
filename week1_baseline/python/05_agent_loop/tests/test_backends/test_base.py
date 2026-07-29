from typing import ClassVar

import pytest

from boukensha.backends.base import Base
from boukensha.errors import UnsupportedModelError


class FakeBackend(Base):
    MODELS: ClassVar[dict[str, dict]] = {
        "model-a": {
            "context_window": 100,
            "cost_per_million": {"input": 1.0, "output": 2.0},
            "usage_unit": "tokens",
        },
        "model-b": {
            "context_window": 200,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "local_compute",
        },
        "model-c": {
            "context_window": 300,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
            "usage_level": "medium",
        },
    }

    def __init__(self, model):
        super().__init__()
        self._configure_model(model)


def test_models_returns_the_class_table():
    assert FakeBackend.models() == FakeBackend.MODELS


def test_models_raises_when_table_undefined():
    class Undefined(Base):
        pass

    with pytest.raises(NotImplementedError, match="Undefined must define MODELS"):
        Undefined.models()


def test_lookup_model_returns_metadata_or_none():
    assert FakeBackend.lookup_model("model-a")["context_window"] == 100
    assert FakeBackend.lookup_model("unknown") is None


def test_validate_model_returns_valid_model():
    assert FakeBackend.validate_model("model-a") == "model-a"


def test_validate_model_raises_with_sorted_supported_list():
    with pytest.raises(UnsupportedModelError, match=r"FakeBackend does not support model 'nope'"):
        FakeBackend.validate_model("nope")

    with pytest.raises(UnsupportedModelError, match=r"Supported models: model-a, model-b, model-c"):
        FakeBackend.validate_model("nope")


def test_instance_accessors_reflect_configured_model():
    backend = FakeBackend("model-a")

    assert backend.model == "model-a"
    assert backend.context_window == 100
    assert backend.input_token_cost_per_million == 1.0
    assert backend.output_token_cost_per_million == 2.0
    assert backend.usage_unit == "tokens"
    assert backend.usage_level is None


def test_usage_level_present_for_models_that_define_it():
    backend = FakeBackend("model-c")
    assert backend.usage_level == "medium"


def test_estimate_cost_normal_priced_model():
    backend = FakeBackend("model-a")
    cost = backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 3.0


def test_estimate_cost_none_when_costs_are_none():
    backend = FakeBackend("model-b")
    assert backend.estimate_cost(input_tokens=100, output_tokens=100) is None


def test_estimate_cost_zero_when_costs_are_zero_not_none():
    backend = FakeBackend("model-c")
    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == 0.0
