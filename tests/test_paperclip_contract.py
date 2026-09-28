from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes_nerve.integrations.paperclip import PaperclipRunContext
from hermes_nerve.integrations.paperclip_client import PaperclipIssue
from hermes_nerve.work.contract import (
    bind_execution_contract,
    issue_to_execution_contract,
    paperclip_run_number,
    parse_definition_of_done,
)
from hermes_nerve.work.supervisor import CardSupervisor


class PaperclipContractTests(unittest.TestCase):
    def context(self):
        return PaperclipRunContext("company", "issue-1", "run-abc", "agent-1")

    def issue(self, description):
        return PaperclipIssue("issue-1", "Fix bug", description, "in_progress")

    def test_parses_only_explicit_dod_section(self):
        text = """Intro
- unrelated

## Definition of Done
- first
- [ ] second
1. third

## Notes
- not a criterion
"""
        self.assertEqual(
            parse_definition_of_done(text),
            ("first", "second", "third"),
        )

    def test_missing_or_empty_dod_fails(self):
        with self.assertRaisesRegex(ValueError, "no explicit"):
            parse_definition_of_done("- tests pass")
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_definition_of_done("## Definition of Done\n\n## Notes\n- nope")

    def test_issue_must_match_trigger(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            issue_to_execution_contract(
                PaperclipIssue("other", "x", "## Definition of Done\n- x", "in_progress"),
                self.context(),
            )

    def test_run_number_is_stable_positive_integer(self):
        first = paperclip_run_number("run-abc")
        self.assertEqual(first, paperclip_run_number("run-abc"))
        self.assertGreater(first, 0)
        self.assertNotEqual(first, paperclip_run_number("run-other"))

    def test_binds_into_real_supervision_store(self):
        with tempfile.TemporaryDirectory() as td:
            supervisor = CardSupervisor(store_path=Path(td) / "work.db")
            execution = issue_to_execution_contract(
                self.issue("## Definition of Done\n- prove x"),
                self.context(),
            )
            identity = bind_execution_contract(
                supervisor, execution, workspace_path=td, session_id="s1"
            )
            self.assertEqual(identity.task_id, "issue-1")
            self.assertEqual(identity.claim_identity, "run-abc")
            self.assertEqual(supervisor.store.current_identity("issue-1"), identity)
            self.assertEqual(
                supervisor.store.run_context(identity)["session_id"], "s1"
            )


if __name__ == "__main__":
    unittest.main()
