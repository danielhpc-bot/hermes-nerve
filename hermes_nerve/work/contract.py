"""Deterministic Paperclip issue -> Nerve Definition-of-Done contract conversion."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from ..integrations.paperclip import PaperclipRunContext
from ..integrations.paperclip_client import PaperclipIssue
from .models import CriterionSpec, DoDContract, RunIdentity


_DOD_HEADING = re.compile(r"^\s*##\s+definition\s+of\s+done\s*$", re.IGNORECASE)
_NEXT_MAJOR_HEADING = re.compile(r"^\s*#{1,2}\s+")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_CHECKBOX = re.compile(r"^\[[ xX]\]\s+(.*\S)\s*$")


def parse_definition_of_done(description: str) -> tuple[str, ...]:
    """Parse only the explicit H2 Definition of Done section; never infer criteria."""
    lines = str(description or "").splitlines()
    start = next((i for i, line in enumerate(lines) if _DOD_HEADING.match(line)), None)
    if start is None:
        raise ValueError("Paperclip issue has no explicit ## Definition of Done section")

    criteria: list[str] = []
    for line in lines[start + 1:]:
        if _NEXT_MAJOR_HEADING.match(line):
            break
        match = _LIST_ITEM.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        checkbox = _CHECKBOX.match(value)
        if checkbox:
            value = checkbox.group(1).strip()
        if value:
            criteria.append(value)
    if not criteria:
        raise ValueError("Paperclip Definition of Done is empty")
    return tuple(criteria)


def build_criteria(statements: tuple[str, ...]) -> tuple[CriterionSpec, ...]:
    return tuple(
        CriterionSpec(id=f"dod-{index}", description=statement)
        for index, statement in enumerate(statements, start=1)
    )


def paperclip_run_number(run_id: str) -> int:
    """Map Paperclip's opaque run id to a stable positive SQLite INTEGER."""
    raw = str(run_id or "").strip()
    if not raw:
        raise ValueError("Paperclip run id is required")
    value = int.from_bytes(hashlib.sha256(raw.encode("utf-8")).digest()[:8], "big")
    return (value & 0x7FFFFFFFFFFFFFFF) or 1


@dataclass(frozen=True)
class PaperclipExecutionContract:
    context: PaperclipRunContext
    issue: PaperclipIssue
    criteria: tuple[CriterionSpec, ...]
    token_budget: int = 0

    @property
    def task_id(self) -> str:
        return self.issue.id


def issue_to_execution_contract(
    issue: PaperclipIssue,
    context: PaperclipRunContext,
    *,
    token_budget: int = 0,
) -> PaperclipExecutionContract:
    if issue.id != context.task_id:
        raise ValueError("Paperclip issue does not match the triggering task")
    return PaperclipExecutionContract(
        context=context,
        issue=issue,
        criteria=build_criteria(parse_definition_of_done(issue.description)),
        token_budget=max(0, int(token_budget or 0)),
    )


def bind_execution_contract(
    supervisor,
    execution: PaperclipExecutionContract,
    *,
    workspace_path: str = "",
    base_revision: str = "",
    session_id: str = "",
) -> RunIdentity:
    """Bind a Paperclip issue into the existing CardSupervisor evidence engine."""
    from types import SimpleNamespace
    from .models import utc_now

    existing = supervisor.active_contract(execution.task_id)
    if existing is None:
        result = supervisor.bind_contract(
            task_id=execution.task_id,
            goal=execution.issue.title,
            criteria=[criterion.as_dict() for criterion in execution.criteria],
            reserve_tokens=execution.token_budget,
            actor="orchestrator",
            preflight_result=SimpleNamespace(
                value="ACCEPT", confidence=1.0, receipt_id="paperclip-contract"
            ),
        )
        if not result.get("accepted"):
            raise RuntimeError("Nerve rejected the Paperclip execution contract")
        existing = supervisor.active_contract(execution.task_id)
    if existing is None:
        raise RuntimeError("Paperclip contract did not become active")

    identity = RunIdentity(
        task_id=execution.task_id,
        run_id=paperclip_run_number(execution.context.run_id),
        contract_hash=existing.contract_hash,
        claim_identity=execution.context.run_id,
        worker_id=execution.context.agent_id,
    )
    supervisor.bind_run(identity)
    supervisor.store.save_run_context(
        identity,
        workspace_path=workspace_path,
        base_revision=base_revision,
        session_id=session_id,
        bound_at=utc_now(),
    )
    return identity
