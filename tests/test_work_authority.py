from __future__ import annotations

import unittest

from hermes_nerve.work.kanban_adapter import HermesKanbanAuthority
from hermes_nerve.work.models import CompletionVerdict


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def request_review(self, **kwargs):
        self.calls.append(kwargs)
        return True, "ok"


class WorkAuthorityTests(unittest.TestCase):
    def test_kanban_adapter_preserves_expected_run_authority(self):
        adapter = FakeAdapter()
        authority = HermesKanbanAuthority(
            task_id="task-1", run_id=42, adapter=adapter, reviewer="reviewer"
        )
        result = authority.request_review(
            CompletionVerdict(
                True, "PASS", 1.0, "verified", receipt_id="deterministic"
            ),
            summary="ready",
            evidence=("test-a",),
        )
        self.assertEqual(result, (True, "ok"))
        self.assertEqual(authority.identity().authority, "hermes_kanban")
        self.assertEqual(adapter.calls[0]["task_id"], "task-1")
        self.assertEqual(adapter.calls[0]["expected_run_id"], 42)
        self.assertEqual(adapter.calls[0]["reviewer"], "reviewer")
        self.assertTrue(
            adapter.calls[0]["metadata"]["hermes_nerve"]["verified"]
        )

    def test_failed_completion_does_not_call_kanban(self):
        adapter = FakeAdapter()
        authority = HermesKanbanAuthority(
            task_id="task-1", run_id=42, adapter=adapter
        )
        result = authority.request_review(
            CompletionVerdict(False, "RETRY", 1.0, "missing")
        )
        self.assertEqual(result, (False, "verification failed"))
        self.assertEqual(adapter.calls, [])


if __name__ == "__main__":
    unittest.main()
