from __future__ import annotations

import unittest

from hermes_nerve.integrations.paperclip_client import (
    HttpResponse,
    PaperclipClient,
    PaperclipTransportError,
)


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.issue = {
            "id": "issue-1",
            "title": "Fix bug",
            "description": "## Definition of Done\n- tests pass",
            "status": "in_progress",
            "projectId": "project-1",
            "assigneeAgentId": "agent-1",
            "checkoutRunId": "run-1",
        }
        self.read_failures = 0

    def request(self, method, url, *, json_body=None, headers=None, timeout=10.0):
        self.calls.append((method, url, json_body, dict(headers or {})))
        if method == "GET":
            if self.read_failures:
                self.read_failures -= 1
                raise OSError("temporary read failure")
            return HttpResponse(200, dict(self.issue))
        if method == "PATCH":
            self.issue.update(json_body or {})
            return HttpResponse(200, dict(self.issue))
        return HttpResponse(405, {"error": "method"})


class PaperclipClientTests(unittest.TestCase):
    def client(self, transport):
        return PaperclipClient(
            base_url="http://paperclip.test",
            token="secret",
            run_id="run-1",
            transport=transport,
        )

    def test_get_issue_is_typed_and_reads_retry(self):
        transport = FakeTransport()
        transport.read_failures = 2
        issue = self.client(transport).get_issue("issue-1")
        self.assertEqual(issue.id, "issue-1")
        self.assertEqual(issue.description.splitlines()[0], "## Definition of Done")
        gets = [call for call in transport.calls if call[0] == "GET"]
        self.assertEqual(len(gets), 3)

    def test_mutation_uses_documented_run_header_and_atomic_patch(self):
        transport = FakeTransport()
        updated = self.client(transport).request_review(
            "issue-1", comment="verified"
        )
        self.assertEqual(updated.status, "in_review")
        patch = [call for call in transport.calls if call[0] == "PATCH"][0]
        self.assertEqual(patch[1], "http://paperclip.test/api/issues/issue-1")
        self.assertEqual(
            patch[2], {"status": "in_review", "comment": "verified"}
        )
        self.assertEqual(patch[3]["X-Paperclip-Run-Id"], "run-1")
        self.assertEqual(patch[3]["Authorization"], "Bearer secret")

    def test_mutation_is_not_blindly_retried(self):
        class Broken(FakeTransport):
            def request(self, method, url, **kwargs):
                if method == "PATCH":
                    self.calls.append((method, url, kwargs.get("json_body"), kwargs.get("headers")))
                    raise OSError("timeout")
                return super().request(method, url, **kwargs)

        transport = Broken()
        with self.assertRaises(PaperclipTransportError):
            self.client(transport).request_review("issue-1", comment="verified")
        self.assertEqual(len([x for x in transport.calls if x[0] == "PATCH"]), 1)


if __name__ == "__main__":
    unittest.main()
