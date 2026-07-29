import os
from pathlib import Path

import boukensha

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

# NOTE: this demo requires a real, reachable CircleMUD server AND a real
# Python port of the separate mud_manager package (week0_explore/mud_manager)
# -- neither is guaranteed to exist wherever this is run. See this step's
# plan (docs/plans/python_port/10_standard_tool_library) for why mud_manager
# is treated as its own, out-of-scope prerequisite rather than ported here.

cfg = boukensha.get_config()
print(f"Config: {cfg}")
print(f"API key set? {os.environ.get('ANTHROPIC_API_KEY') is not None}")
print()

boukensha.run(
    task=(
        "Connect to the MUD, look at your surroundings, check your score, "
        "then look at the available exits and tell me what you see."
    ),
    # system/model/api_key all come from config automatically
    working_dir=False,  # no filesystem tools needed for MUD play
    # mud: comes from config (settings.toml [mud] section) automatically
)
