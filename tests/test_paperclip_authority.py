from __future__ import annotations

import unittest

from hermes_nerve.integrations.paperclip import PaperclipRunContext
from hermes_nerve.integrations.paperclip_client import HttpResponse, PaperclipClient, PaperclipIssue
from hermes_nerve.work.contract import issue_to_execution_contract
from hermes_nerve.work.models import CompletionVerdict
from hermes_nerve.work.paperclip_authority import PaperclipIssueAuthority


class FakeTransport:
    def __init__(self, *, timeout_after_commit=False):
        self.calls = []
        self.timeout_after_commit = timeout_after_commit
        self.issue = {
            "id": "issue-1",
            "title": "Fix",
            "description": "## Definition of Done\n- x",
            "status": "in_progress",
            "assigneeAgentId": "agent-1",
            "checkoutRunId": "run-1",
        }

    def request(self, method, url, *, json_body=None, headers=None, timeout=10):
        self.calls.append((method, url, json_body, headers))
        if method == "GET":
            return HttpResponse(200, dict(self.issue))
        if method == "PATCH":
            self.issue.update(json_body or {})
            if self.timeout_after_commit:
                self.timeout_after_commit = False
                raise OSError("response lost")
            return HttpResponse(200, dict(self.issue))
        raise AssertionError(method)


def build(transport):
    context = PaperclipRunContext("company", "issue-1", "run-1", "agent-1")
    issue = PaperclipIssue(
        "issue-1", "Fix", "## Definition of Done\n- x", "in_progress",
        assignee_agent_id="agent-1", checkout_run_id="run-1",
    )
    execution = issue_to_execution_contract(issue, context)
    client = PaperclipClient(
        base_url="http://paperclip.test",
        token="token",
        run_id="run-1",
        transport=transport,
    )
    return PaperclipIssueAuthority(client, execution)


class PaperclipAuthorityTests(unittest.TestCase):
    def test_failed_verification_does_not_advance(self):
        transport = FakeTransport()
        outcome = build(transport).request_review(
            CompletionVerdict(False, "NEEDS_EVIDENCE", 1.0, "missing")
        )
        self.assertFalse(outcome.local_pass)
        self.assertFalse(outcome.remote_updated)
        self.assertFalse(any(call[0] == "PATCH" for call in transport.calls))

    def test_pass_advances_once(self):
        transport = FakeTransport()
        authority = build(transport)
        verdict = CompletionVerdict(True, "PASS", 1.0, "verified", receipt_id="deterministic")
        self.assertTrue(authority.request_review(verdict).remote_updated)
        self.assertTrue(authority.request_review(verdict).remote_updated)
        patches = [call for call in transport.calls if call[0] == "PATCH"]
        self.assertEqual(len(patches), 1)
        self.assertIn("### Nerve Verification", patches[0][2]["comment"])
        self.assertIn("nerve-verification:run-1", patches[0][2]["comment"])

    def test_timeout_after_server_commit_reconciles_without_duplicate_patch(self):
        transport = FakeTransport(timeout_after_commit=True)
        outcome = build(transport).request_review(
            CompletionVerdict(True, "PASS", 1.0, "verified")
        )
        self.assertTrue(outcome.local_pass)
        self.assertTrue(outcome.remote_updated)
        self.assertEqual(
            len([call for call in transport.calls if call[0] == "PATCH"]), 1
        )

    def test_stale_run_cannot_advance_issue(self):
        transport = FakeTransport()
        transport.issue["checkoutRunId"] = "run-new"
        outcome = build(transport).request_review(
            CompletionVerdict(True, "PASS", 1.0, "verified")
        )
        self.assertTrue(outcome.local_pass)
        self.assertFalse(outcome.remote_updated)
        self.assertIn("different run", outcome.reason)
        self.assertFalse(any(call[0] == "PATCH" for call in transport.calls))

    def test_already_in_review_is_success_even_if_reviewer_owns_new_checkout(self):
        transport = FakeTransport()
        transport.issue["status"] = "in_review"
        transport.issue["checkoutRunId"] = "review-run"
        transport.issue["assigneeAgentId"] = "reviewer-1"
        outcome = build(transport).request_review(
            CompletionVerdict(True, "PASS", 1.0, "verified")
        )
        self.assertTrue(outcome.local_pass)
        self.assertTrue(outcome.remote_updated)
        self.assertEqual(outcome.reason, "already handed off")
        self.assertFalse(any(call[0] == "PATCH" for call in transport.calls))


if __name__ == "__main__":
    unittest.main()
