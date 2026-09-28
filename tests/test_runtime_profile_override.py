from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hermes_nerve.config_resolver import resolve_config
from hermes_nerve.profiles import save_profile


class RuntimeProfileOverrideTests(unittest.TestCase):
    def test_paperclip_role_overrides_persisted_profile_without_mutating_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save_profile({
                "version": 1,
                "nerve_profile": "operator",
                "nerve_modules": {},
                "advanced": {},
            }, root)
            path = root / "nerve" / "profile.json"
            before = path.read_bytes()
            with patch.dict("os.environ", {"PAPERCLIP_AGENT_ROLE": "builder"}, clear=False):
                resolved = resolve_config(home=root)
            self.assertEqual(resolved.profile, "lean")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(path.read_text())["nerve_profile"], "operator")

    def test_explicit_runtime_profile_overrides_plugin_config(self):
        getter = lambda key, default=None: "operator" if key == "nerve_profile" else default
        resolved = resolve_config(getter, profile={
            "version": 1,
            "nerve_profile": "marie_kondo",
            "nerve_modules": {},
            "advanced": {},
        }, runtime_profile="fat_cat")
        self.assertEqual(resolved.profile, "fat_cat")

    def test_no_runtime_override_preserves_existing_resolution(self):
        resolved = resolve_config(profile={
            "version": 1,
            "nerve_profile": "operator",
            "nerve_modules": {},
            "advanced": {},
        }, runtime_profile="")
        self.assertEqual(resolved.profile, "operator")


if __name__ == "__main__":
    unittest.main()
