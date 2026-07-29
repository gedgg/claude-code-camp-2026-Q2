from __future__ import annotations


class RunDSL:
    """The object handed to a run()/repl() `register` callable. Exposes only
    `tool`, keeping the DSL surface intentionally small.

    Ruby's `Boukensha.run(...) { tool ... }` uses `instance_eval` so bare
    `tool(...)` calls inside the block resolve against a RunDSL instance —
    Python has no equivalent mechanism, so callers here receive the RunDSL
    instance explicitly: `boukensha.run(task="...", register=lambda dsl:
    dsl.tool(...))`.
    """

    def __init__(self, registry) -> None:
        self._registry = registry

    def tool(self, name, *, description, parameters=None, block=None):
        return self._registry.tool(name, description=description, parameters=parameters, block=block)
