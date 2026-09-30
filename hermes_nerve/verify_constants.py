"""Central constants for decomposed worker verification (TypeSafe pattern).

Single reviewable place for the questions and the verdict table used by
``DecisionEngine.verify_decomposed`` — per the TypeSafe agent-skill guidance:
keep questions/thresholds in one file so humans can review them without
spelunking. Noul answers carry P(yes) directly; no separate confidence.
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Questions — one narrow judgment each, all asked together over the same state
# (independent questions over shared state run in a single request).
# ---------------------------------------------------------------------------

EVIDENCE_SUFFICIENT: Final[dict[str, Any]] = {
    "type": "noul",
    "instructions": (
        "Judging ONLY the worker outcome evidence in `outcome`: does the evidence "
        "genuinely show the requested outcome was achieved? Evidence that reveals a "
        "platform/environment limitation that blocks the goal counts as NOT sufficient. "
        "Do not consider what to do next — another question covers that."
    ),
}

APPROACH_VIABLE: Final[dict[str, Any]] = {
    "type": "noul",
    "instructions": (
        "Judging ONLY the worker's approach in `outcome`: is the current approach "
        "(plan, method, environment) viable for achieving the goal if execution is "
        "retried or continued as-is? An approach defeated by a hard environment "
        "limitation, or one that cannot achieve the goal at all, is NOT viable. "
        "An unstable or flaky test with a sound method IS still viable: the method "
        "stands, the run should simply be repeated."
    ),
}

NEEDS_HUMAN: Final[dict[str, Any]] = {
    "type": "noul",
    "instructions": (
        "Judging ONLY the situation in `outcome`: does resolving this require human "
        "judgment, explicit permission, missing information only a person has, or an "
        "external dependency outside the worker's control? Automated failures that "
        "code can fix do NOT require a human."
    ),
}

QUESTIONS: Final[dict[str, dict[str, Any]]] = {
    "evidence_sufficient": EVIDENCE_SUFFICIENT,
    "approach_viable": APPROACH_VIABLE,
    "needs_human": NEEDS_HUMAN,
}

# ---------------------------------------------------------------------------
# Verdict table — code combines the three P(yes) values, no model re-call.
# Evaluated in order; first match wins.
# ---------------------------------------------------------------------------


def verdict_from(p_evidence: float, p_approach: float, p_human: float) -> tuple[str, float]:
    """Map the three Noul probabilities to a verify/v1-compatible verdict.

    Returns ``(verdict, strength)`` where strength is the probability that
    supports the verdict (for receipts/audits).
    """
    if p_human >= NEEDS_HUMAN_THRESHOLD:
        return "ESCALATE", p_human
    if p_evidence >= PASS_THRESHOLD and p_approach >= APPROACH_THRESHOLD:
        return "PASS", min(p_evidence, p_approach)
    if p_approach < REPLAN_THRESHOLD:
        return "REPLAN", 1.0 - p_approach
    return "RETRY", max(p_evidence, 1.0 - p_human)


# Thresholds — calibrated against live Jev runs on this machine (25/09/2026), not guessed.
# Observed distributions: clear PASS evidence_sufficient 0.72-0.89; unresolved failure 0.03-0.11;
# sound-but-flaky approach_viable 0.28; unsound plan 0.09; human-gated needs_human 0.86-0.94.
# ESCALATE wins first because putting a human in the loop is the safe default.
NEEDS_HUMAN_THRESHOLD: Final[float] = 0.70
PASS_THRESHOLD: Final[float] = 0.70
APPROACH_THRESHOLD: Final[float] = 0.60
REPLAN_THRESHOLD: Final[float] = 0.20
