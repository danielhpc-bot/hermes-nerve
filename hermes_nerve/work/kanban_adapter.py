from __future__ import annotations

from typing import Any

from .authority import WorkIdentity
from .models import CompletionVerdict


class CanonicalKanbanAdapter:
    """Thin adapter over Hermes' canonical kanban_db API.

    No lifecycle state is mirrored here. If Hermes Kanban is unavailable, the
    adapter reports that explicitly instead of inventing a replacement board.
    """

    def __init__(self, kb_module: Any | None = None) -> None:
        self._kb = kb_module

    def _module(self):
        if self._kb is not None:
            return self._kb
        try:
            from hermes_cli import kanban_db as kb  # type: ignore
        except Exception as exc:
            raise RuntimeError("Hermes canonical kanban_db is not importable") from exc
        self._kb = kb
        return kb

    def request_review(
        self,
        *,
        task_id: str,
        expected_run_id: int,
        summary: str,
        metadata: dict[str, Any],
        reviewer: str = "",
    ) -> tuple[bool, str | None]:
        kb = self._module()
        with kb.connect_closing() as conn:
            result = kb.request_review(
                conn,
                task_id,
                summary=summary,
                metadata=metadata,
                reviewer=reviewer or None,
                expected_run_id=int(expected_run_id),
                force=False,
                with_reason=True,
            )
        if isinstance(result, tuple):
            return bool(result[0]), result[1]
        return bool(result), None if result else "canonical review transition failed"

    def complete(
        self,
        *,
        task_id: str,
        expected_run_id: int,
        result: str | None = None,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        kb = self._module()
        with kb.connect_closing() as conn:
            return bool(
                kb.complete_task(
                    conn,
                    task_id,
                    result=result,
                    summary=summary,
                    metadata=metadata,
                    expected_run_id=int(expected_run_id),
                )
            )


class HermesKanbanAuthority:
    """Expose canonical Hermes Kanban review as a WorkAuthority."""

    def __init__(
        self,
        *,
        task_id: str,
        run_id: int,
        adapter: CanonicalKanbanAdapter | None = None,
        reviewer: str = "",
    ) -> None:
        self.task_id = str(task_id)
        self.run_id = int(run_id)
        self.adapter = adapter or CanonicalKanbanAdapter()
        self.reviewer = str(reviewer or "")

    def identity(self) -> WorkIdentity:
        return WorkIdentity("hermes_kanban", self.task_id, str(self.run_id))

    def request_review(
        self,
        result: CompletionVerdict,
        *,
        summary: str = "",
        evidence: tuple[str, ...] = (),
    ):
        if not result.allow:
            return False, "verification failed"
        metadata = {
            "hermes_nerve": {
                "verified": True,
                "receipt_id": str(result.receipt_id or ""),
                "confidence": float(result.confidence or 0.0),
                "evidence": list(evidence),
            }
        }
        return self.adapter.request_review(
            task_id=self.task_id,
            expected_run_id=self.run_id,
            summary=str(summary or result.reason),
            metadata=metadata,
            reviewer=self.reviewer,
        )

    def report_blocked(self, reason: str):
        # Existing Kanban block authority remains with Hermes lifecycle tools.
        return False, str(reason or "")
