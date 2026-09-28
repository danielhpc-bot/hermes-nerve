"""Runtime bridge between Paperclip issue runs and Nerve CardSupervisor."""
from __future__ import annotations

from contextvars import ContextVar
import os
from pathlib import Path
import subprocess
from typing import Any

from ..integrations.paperclip import PaperclipRunContext, detect_paperclip_context
from ..integrations.paperclip_client import PaperclipClient
from .contract import bind_execution_contract, issue_to_execution_contract
from .models import CompletionVerdict, RunIdentity
from .paperclip_authority import HandoffResult, PaperclipIssueAuthority


_ACTIVE: ContextVar[tuple[RunIdentity, PaperclipIssueAuthority] | None] = ContextVar(
    "nerve_paperclip_active", default=None
)


def _git_head(workspace: str) -> str:
    root = str(workspace or "").strip()
    if not root or not Path(root).is_dir():
        return ""
    try:
        proc = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def client_from_env(context: PaperclipRunContext) -> PaperclipClient:
    return PaperclipClient(
        base_url=context.api_url or os.getenv("PAPERCLIP_API_URL", ""),
        token=os.getenv("PAPERCLIP_API_KEY", ""),
        run_id=context.run_id,
    )


def bootstrap_paperclip_worker(
    supervisor,
    *,
    context: PaperclipRunContext | None = None,
    client: PaperclipClient | None = None,
    workspace_path: str = "",
    session_id: str = "",
    token_budget: int = 0,
) -> RunIdentity | None:
    """Bind the triggering Paperclip issue into the existing Nerve evidence engine."""
    context = context or detect_paperclip_context()
    if context is None:
        return None
    client = client or client_from_env(context)
    issue = client.get_issue(context.task_id)
    execution = issue_to_execution_contract(
        issue, context, token_budget=token_budget
    )
    workspace = str(
        workspace_path
        or os.getenv("PAPERCLIP_WORKSPACE")
        or os.getenv("TERMINAL_CWD")
        or os.getenv("PWD")
        or ""
    ).strip()
    identity = bind_execution_contract(
        supervisor,
        execution,
        workspace_path=workspace,
        base_revision=_git_head(workspace),
        session_id=session_id,
    )
    authority = PaperclipIssueAuthority(client, execution)
    _ACTIVE.set((identity, authority))
    return identity


def current_identity() -> RunIdentity | None:
    active = _ACTIVE.get()
    return active[0] if active else None


def current_authority() -> PaperclipIssueAuthority | None:
    active = _ACTIVE.get()
    return active[1] if active else None


def owns(identity: RunIdentity | None) -> bool:
    current = current_identity()
    return bool(identity is not None and current == identity)


def request_review(
    supervisor,
    identity: RunIdentity,
    verdict: CompletionVerdict,
    *,
    summary: str = "",
) -> HandoffResult:
    if not owns(identity):
        return HandoffResult(bool(verdict.allow), False, "Paperclip run is not active")
    authority = current_authority()
    if authority is None:
        return HandoffResult(bool(verdict.allow), False, "Paperclip authority unavailable")
    evidence = tuple(
        str(row.get("pointer") or row.get("tool_name") or row.get("kind") or "").strip()
        for row in supervisor.store.evidence(identity)
        if str(row.get("pointer") or row.get("tool_name") or row.get("kind") or "").strip()
    )
    return authority.request_review(
        verdict,
        summary=summary,
        evidence=evidence[-12:],
    )


def clear_for_tests() -> None:
    _ACTIVE.set(None)
