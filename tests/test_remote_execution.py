from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from hermes_nerve.remote import runtime
from hermes_nerve.remote.config import resolve_host
from hermes_nerve.remote.errors import RemoteWorkerError
from hermes_nerve.remote.execution import RemoteManager
from hermes_nerve.remote.protocol import ProtocolState
from hermes_nerve.remote.util import sanitized_subprocess_env


class RemoteExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fake = Path(__file__).with_name("fake_ssh.py").resolve()
        runtime.configure(
            hosts={
                "lab": {
                    "ssh_host": "fake-host",
                    "workspace_root": "/srv/work",
                    "default_workspace": "repo",
                    "ssh_binary": str(self.fake),
                    "hermes_binary": "hermes",
                    "task_timeout_seconds": 30,
                    "max_turns": 25,
                }
            },
            default_host="lab",
            data_dir=str(self.root / "remote"),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_local_runner_env_strips_parent_kanban_identity(self):
        ambient = {
            "HERMES_KANBAN_TASK": "ambient-task",
            "HERMES_KANBAN_TASK_ID": "ambient-id",
            "HERMES_KANBAN_RUN_ID": "7",
            "HERMES_KANBAN_CLAIM_IDENTITY": "claim",
            "HERMES_KANBAN_WORKER_ID": "worker",
            "HERMES_NERVE_DOD_HASH": "hash",
            "KEEP_ME": "yes",
        }
        with patch.dict(os.environ, ambient, clear=False):
            child = sanitized_subprocess_env()
        for key in ambient:
            if key != "KEEP_ME":
                self.assertNotIn(key, child)
        self.assertEqual(child["KEEP_ME"], "yes")

    def test_admin_alias_and_workspace_containment(self):
        host = resolve_host(runtime.settings(), requested_alias="lab", workspace="repo/sub")
        self.assertEqual(host.workspace, "/srv/work/repo/sub")
        with self.assertRaises(RemoteWorkerError):
            resolve_host(runtime.settings(), requested_alias="lab", workspace="../escape")
        with self.assertRaises(RemoteWorkerError):
            resolve_host(runtime.settings(), requested_alias="-oProxyCommand=bad")

    def test_durable_remote_job_task_is_stdin_not_argv(self):
        log = self.root / "ssh.json"
        env = {"FAKE_SSH_LOG": str(log), "FAKE_SSH_MODE": "success"}
        with patch.dict(os.environ, env, clear=False):
            execution = RemoteManager().start(host_alias="lab", goal="SECRET_GOAL_TOKEN", context="ctx")
            first = execution.status()
            self.assertIn(first["status"], {"starting", "running", "completed"})
            job = execution.wait(timeout=10)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result_text"], "REMOTE_OK")
        argv = json.loads(log.read_text())["argv"]
        self.assertNotIn("SECRET_GOAL_TOKEN", " ".join(argv))
        self.assertIn("SECRET_GOAL_TOKEN", Path(str(log) + ".stdin").read_text())

    def test_cancel_is_durable(self):
        with patch.dict(os.environ, {"FAKE_SSH_MODE": "sleep"}, clear=False):
            execution = RemoteManager().start(host_alias="lab", goal="long task")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and execution.status()["status"] == "starting":
                time.sleep(0.05)
            execution.cancel()
            job = execution.wait(timeout=10)
        self.assertEqual(job["status"], "cancelled")

    def test_rate_limit_exit_75_is_preserved(self):
        with patch.dict(os.environ, {"FAKE_SSH_MODE": "rate_limit"}, clear=False):
            execution = RemoteManager().start(host_alias="lab", goal="quota task")
            job = execution.wait(timeout=10)
        self.assertEqual(job["status"], "rate_limited")
        self.assertEqual(job["exit_code"], 75)
        self.assertEqual(job["error_code"], "rate_limited")

    def test_protocol_tracks_session_and_result(self):
        proto = ProtocolState()
        proto.consume_line(json.dumps({"type":"system","subtype":"init","session_id":"s1"}))
        proto.consume_line(json.dumps({"type":"result","session_id":"s1","exit_code":0,"text":"ok"}))
        self.assertEqual(proto.remote_session_id, "s1")
        self.assertEqual(proto.result_event["text"], "ok")


if __name__ == "__main__":
    unittest.main()