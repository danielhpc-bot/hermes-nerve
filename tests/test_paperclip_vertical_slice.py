from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes_nerve.integrations.paperclip import PaperclipRunContext
from hermes_nerve.integrations.paperclip_client import HttpResponse, PaperclipClient
from hermes_nerve.work import hooks, paperclip_runtime, runtime
from hermes_nerve.work.supervisor import CardSupervisor


class FakePaperclip:
    def __init__(self, description: str, *, timeout_after_commit: bool = False):
        self.calls = []
        self.timeout_after_commit = timeout_after_commit
        self.issue = {
            "id": "issue-e2e",
            "title": "Repair fixture",
            "description": description,
            "status": "in_progress",
            "assigneeAgentId": "builder-1",
            "checkoutRunId": "run-e2e",
        }

    def request(self, method, url, *, json_body=None, headers=None, timeout=10.0):
        self.calls.append((method, url, json_body, dict(headers or {})))
        if method == "GET":
            return HttpResponse(200, dict(self.issue))
        if method == "PATCH":
            self.issue.update(json_body or {})
            if self.timeout_after_commit:
                self.timeout_after_commit = False
                raise OSError("response lost after commit")
            return HttpResponse(200, dict(self.issue))
        raise AssertionError(method)


class PaperclipVerticalSliceTests(unittest.TestCase):
    def tearDown(self):
        paperclip_runtime.clear_for_tests()
        runtime.set_supervisor_for_tests(None, enabled_value=False)

    @staticmethod
    def context():
        return PaperclipRunContext(
            "company-1", "issue-e2e", "run-e2e", "builder-1",
            api_url="http://paperclip.test",
            role="builder",
        )

    @staticmethod
    def client(transport):
        return PaperclipClient(
            base_url="http://paperclip.test",
            token="token",
            run_id="run-e2e",
            transport=transport,
        )

    def _supervisor(self, root: Path):
        supervisor = CardSupervisor(store_path=root / "work.db")
        runtime.set_supervisor_for_tests(supervisor, enabled_value=True)
        return supervisor

    def test_real_supervisor_runs_deterministic_suite_then_requests_review(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_ok.py").write_text(
                "import unittest\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self): self.assertEqual(2 + 2, 4)\n"
            )
            description = (
                "## Definition of Done\n"
                "- \`python -m unittest discover -s tests -q\` exits 0.\n"
            )
            remote = FakePaperclip(description)
            supervisor = self._supervisor(root)
            identity = paperclip_runtime.bootstrap_paperclip_worker(
                supervisor,
                context=self.context(),
                client=self.client(remote),
                workspace_path=td,
                session_id="session-e2e",
            )
            self.assertIsNotNone(identity)

            decision = hooks.pre_verify(
                task_id="issue-e2e",
                session_id="session-e2e",
                final_response="Implemented and tested.",
            )

            self.assertIsNone(decision)
            self.assertEqual(remote.issue["status"], "in_review")
            patches = [call for call in remote.calls if call[0] == "PATCH"]
            self.assertEqual(len(patches), 1)
            self.assertIn("### Nerve Verification", patches[0][2]["comment"])
            verdicts = supervisor.store.latest_contract_verdicts(
                identity.task_id, identity.contract_hash
            )
            self.assertEqual(verdicts["dod-1"]["state"], "VERIFIED_PASS")
            evidence = supervisor.store.evidence(identity)
            self.assertTrue(any(row["kind"] == "deterministic_check" for row in evidence))

            self.assertIsNone(hooks.pre_verify(task_id="issue-e2e"))
            self.assertEqual(
                len([call for call in remote.calls if call[0] == "PATCH"]), 1
            )

    def test_fake_completion_without_evidence_stays_in_progress(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            remote = FakePaperclip(
                "## Definition of Done\n- Explain the root cause with supporting evidence.\n"
            )
            supervisor = self._supervisor(root)
            paperclip_runtime.bootstrap_paperclip_worker(
                supervisor,
                context=self.context(),
                client=self.client(remote),
                workspace_path=td,
            )
            decision = hooks.pre_verify(
                task_id="issue-e2e",
                final_response="Trust me, it is done.",
            )
            self.assertEqual(decision["action"], "continue")
            self.assertEqual(remote.issue["status"], "in_progress")
            self.assertFalse(any(call[0] == "PATCH" for call in remote.calls))

    def test_failed_deterministic_criterion_stays_in_progress(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_bad.py").write_text(
                "import unittest\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_bad(self): self.fail('still broken')\n"
            )
            remote = FakePaperclip(
                "## Definition of Done\n"
                "- \`python -m unittest discover -s tests -q\` exits 0.\n"
            )
            supervisor = self._supervisor(root)
            paperclip_runtime.bootstrap_paperclip_worker(
                supervisor,
                context=self.context(),
                client=self.client(remote),
                workspace_path=td,
            )
            decision = hooks.pre_verify(task_id="issue-e2e")
            self.assertEqual(decision["action"], "continue")
            self.assertEqual(remote.issue["status"], "in_progress")
            self.assertFalse(any(call[0] == "PATCH" for call in remote.calls))

    def test_timeout_after_remote_commit_is_reconciled(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_ok.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_ok(self): self.assertTrue(True)\n"
            )
            remote = FakePaperclip(
                "## Definition of Done\n"
                "- \`python -m unittest discover -s tests -q\` exits 0.\n",
                timeout_after_commit=True,
            )
            supervisor = self._supervisor(root)
            paperclip_runtime.bootstrap_paperclip_worker(
                supervisor,
                context=self.context(),
                client=self.client(remote),
                workspace_path=td,
            )
            self.assertIsNone(hooks.pre_verify(task_id="issue-e2e"))
            self.assertEqual(remote.issue["status"], "in_review")
            self.assertEqual(
                len([call for call in remote.calls if call[0] == "PATCH"]), 1
            )


if __name__ == "__main__":
    unittest.main()
