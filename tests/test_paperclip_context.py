from __future__ import annotations

import unittest

from hermes_nerve.integrations.paperclip import (
    PaperclipRunContext,
    detect_paperclip_context,
    runtime_profile_override,
)


class PaperclipContextTests(unittest.TestCase):
    def test_no_context(self):
        self.assertIsNone(detect_paperclip_context({}))

    def test_valid_context_uses_documented_task_id(self):
        ctx = detect_paperclip_context({
            "PAPERCLIP_COMPANY_ID": "c1",
            "PAPERCLIP_TASK_ID": "issue-7",
            "PAPERCLIP_RUN_ID": "run-9",
            "PAPERCLIP_AGENT_ID": "agent-2",
            "PAPERCLIP_API_URL": "http://127.0.0.1:3100",
            "PAPERCLIP_API_KEY": "must-not-be-retained",
            "PAPERCLIP_AGENT_ROLE": "Builder",
        })
        self.assertEqual(
            ctx,
            PaperclipRunContext(
                company_id="c1",
                task_id="issue-7",
                run_id="run-9",
                agent_id="agent-2",
                api_url="http://127.0.0.1:3100",
                role="builder",
            ),
        )
        self.assertFalse(hasattr(ctx, "api_key"))

    def test_partial_context_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "PAPERCLIP_RUN_ID"):
            detect_paperclip_context({
                "PAPERCLIP_COMPANY_ID": "c1",
                "PAPERCLIP_TASK_ID": "issue-7",
                "PAPERCLIP_AGENT_ID": "agent-2",
            })

    def test_blank_required_value_is_missing(self):
        with self.assertRaisesRegex(ValueError, "PAPERCLIP_AGENT_ID"):
            detect_paperclip_context({
                "PAPERCLIP_COMPANY_ID": "c1",
                "PAPERCLIP_TASK_ID": "issue-7",
                "PAPERCLIP_RUN_ID": "run-9",
                "PAPERCLIP_AGENT_ID": "  ",
            })

    def test_explicit_runtime_profile_wins_over_role_mapping(self):
        override = runtime_profile_override({
            "HERMES_NERVE_RUNTIME_PROFILE": "fat-cat",
            "PAPERCLIP_AGENT_ROLE": "builder",
        })
        self.assertEqual(override.profile, "fat_cat")
        self.assertEqual(override.source, "environment")

    def test_role_mapping(self):
        self.assertEqual(runtime_profile_override({"PAPERCLIP_AGENT_ROLE": "builder"}).profile, "lean")
        self.assertEqual(runtime_profile_override({"PAPERCLIP_AGENT_ROLE": "reviewer"}).profile, "fat_cat")
        self.assertIsNone(runtime_profile_override({"PAPERCLIP_AGENT_ROLE": "unknown"}))

    def test_unknown_explicit_runtime_profile_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown runtime Nerve profile"):
            runtime_profile_override({"HERMES_NERVE_RUNTIME_PROFILE": "turbo"})


if __name__ == "__main__":
    unittest.main()
