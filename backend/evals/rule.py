"""The fixed selection rule's constants (ai.md section 4), defined ONCE.

Weights approved by the user on 2026-11-14. Change nothing here without a new approval; the test
`test_selection_weights_are_0_5_0_3_0_2` asserts these values.
"""

from typing import Final

# Hard gates.
SAFETY_RECALL_MIN: Final = 1.0
MAX_SCHEMA_FAILURE_RATE: Final = 0.005
MAX_TIMEOUT_RATE: Final = 0.0
TIMEOUT_BUDGET_SECONDS: Final = 12.0  # per-turn budget the timeout rate is measured against
MAX_P95_LATENCY_SECONDS: Final = 5.0

# Ranking weights (sum to 1) and the near-tie margin.
WEIGHT_ACCURACY: Final = 0.5
WEIGHT_QUALITY: Final = 0.3
WEIGHT_CONSISTENCY: Final = 0.2
TIE_MARGIN: Final = 0.02

# Turns in one completed lesson (cost per lesson).
LESSON_TURNS: Final = 3
# Runs per case used to measure consistency.
CONSISTENCY_RUNS: Final = 3
