"""Lifecycle-authority seam for supervised work."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from .models import CompletionVerdict


@dataclass(frozen=True)
class WorkIdentity:
    authority: Literal["hermes_kanban", "paperclip"]
    task_id: str
    run_id: str


class WorkAuthority(Protocol):
    def identity(self) -> WorkIdentity:
        ...

    def request_review(
        self,
        result: CompletionVerdict,
        *,
        summary: str = "",
        evidence: tuple[str, ...] = (),
    ) -> Any:
        ...

    def report_blocked(self, reason: str) -> Any:
        ...
