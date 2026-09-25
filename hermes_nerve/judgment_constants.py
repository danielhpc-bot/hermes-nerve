"""Central constants for TypeSafe-assisted judgments that replace fragile parsing.

Single reviewable place for the questions and thresholds used by
``router.infer_tool_risk`` (Noul fallback) and ``work.deterministic``
(exit-code cascade) — per the TypeSafe agent-skill guidance: keep
questions/thresholds in one file so humans can review them.
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Tool-risk judgment — replaces substring hint matching when hints are
# inconclusive (e.g. "catalog_publish" falsely matching "cat").
# ---------------------------------------------------------------------------

IS_MUTATING: Final[dict[str, Any]] = {
    "type": "noul",
    "instructions": (
        "Judging ONLY the tool in `tool`: does this tool, by its name and "
        "`description`, mutate persistent state — create, modify or delete data, "
        "or affect systems outside this process (send, publish, deploy)? Pure "
        "reads, computations and listings are not mutations."
    ),
}

# Decision policy for infer_tool_risk:
#   hints agree            -> keep deterministic hint result (no network)
#   hints inconclusive     -> ask Noul; noul >= MUTATING_THRESHOLD -> mutating risk
#                             noul <= READ_ONLY_THRESHOLD -> read-only risk
#                             in between  -> unknown-tool risk (conservative middle)
#   provider unavailable   -> unknown-tool risk (never block on network)
MUTATING_THRESHOLD: Final[float] = 0.80
READ_ONLY_THRESHOLD: Final[float] = 0.20

# ---------------------------------------------------------------------------
# Test-output cascade — regex first; when ambiguous, one Noul judgment.
# ---------------------------------------------------------------------------

SUITE_PASSED: Final[dict[str, Any]] = {
    "type": "noul",
    "instructions": (
        "Judging ONLY the `output` text: does it indicate the test suite "
        "ultimately passed with no unresolved failure? Retries that later "
        "succeeded count as passed; any failure or error left unresolved "
        "counts as not passed."
    ),
}

# Use the Noul judgment only when regex evidence is ambiguous; treat
# P(pass) >= SUITE_PASS_THRESHOLD as exit 0, P(pass) <= SUITE_FAIL_THRESHOLD
# as exit 1, anything between stays ambiguous (None).
SUITE_PASS_THRESHOLD: Final[float] = 0.75
SUITE_FAIL_THRESHOLD: Final[float] = 0.25
