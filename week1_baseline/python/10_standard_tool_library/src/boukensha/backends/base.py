from __future__ import annotations

from typing import ClassVar

from boukensha.errors import UnsupportedModelError


class Base:
    """Shared contract every backend implements: a class-level MODELS table,
    model validation, and cost/window accessors for the configured model."""

    MODELS: ClassVar[dict[str, dict]] = {}

    def __init__(self) -> None:
        self.model: str | None = None
        self._model_info: dict | None = None

    @classmethod
    def models(cls) -> dict[str, dict]:
        if not cls.MODELS:
            raise NotImplementedError(f"{cls.__name__} must define MODELS")
        return cls.MODELS

    @classmethod
    def lookup_model(cls, model: str) -> dict | None:
        return cls.models().get(str(model))

    @classmethod
    def validate_model(cls, model: str) -> str:
        model = str(model)
        if cls.lookup_model(model):
            return model

        supported = ", ".join(sorted(cls.models().keys()))
        raise UnsupportedModelError(f"{cls.__name__} does not support model '{model}'. Supported models: {supported}")

    @property
    def model_info(self) -> dict:
        return self._model_info

    @property
    def context_window(self) -> int:
        return self.model_info["context_window"]

    @property
    def input_token_cost_per_million(self) -> float | None:
        return self.model_info["cost_per_million"]["input"]

    @property
    def output_token_cost_per_million(self) -> float | None:
        return self.model_info["cost_per_million"]["output"]

    @property
    def usage_unit(self) -> str:
        return self.model_info["usage_unit"]

    @property
    def usage_level(self) -> str | None:
        return self.model_info.get("usage_level")

    def estimate_cost(self, *, input_tokens: int, output_tokens: int) -> float | None:
        input_cost = self.input_token_cost_per_million
        output_cost = self.output_token_cost_per_million
        if input_cost is None or output_cost is None:
            return None

        return ((input_tokens * input_cost) + (output_tokens * output_cost)) / 1_000_000.0

    def _configure_model(self, model: str) -> None:
        self.model = self.validate_model(model)
        self._model_info = self.lookup_model(self.model)
