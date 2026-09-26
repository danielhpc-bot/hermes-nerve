import os, sqlite3, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from hermes_nerve.integrations import shared_context

MANIFEST='name: hermes-context-bus\nversion: "0.2.0"\nprovides_tools:\n  - shared_context_health\n'

class SharedContextAdapterTests(unittest.TestCase):
    def test_detect_absent(self):
        with tempfile.TemporaryDirectory() as td:
            st=shared_context.detect(Path(td)); self.assertFalse(st["installed"]); self.assertEqual(st["authority"],"coordination-data-only")

    def _source(self,root,version="0.2.0",health=True):
        src=Path(root); tools='provides_tools:\n  - shared_context_health\n' if health else 'provides_tools: []\n'
        (src/"plugin.yaml").write_text(f'name: hermes-context-bus\nversion: "{version}"\n'+tools); (src/"README.md").write_text("bus"); return src

    def test_install_from_source_is_external_copy(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as home:
            src=self._source(source); (src/"runtime").mkdir(); (src/"runtime"/"secret").write_text("runtime"); (src/"state").mkdir(); (src/"state"/"db").write_text("state")
            st=shared_context.install_from_source(src,Path(home)); target=Path(st["path"])
            self.assertTrue(st["installed"]); self.assertTrue(st["compatible"]); self.assertTrue((target/"README.md").exists()); self.assertFalse((target/"runtime").exists()); self.assertFalse((target/"state").exists())

    def test_detect_v02_manifest_and_schema(self):
        with tempfile.TemporaryDirectory() as home:
            root=Path(home); target=root/"plugins"/"hermes-context-bus"; target.mkdir(parents=True); (target/"plugin.yaml").write_text(MANIFEST)
            db=root/"shared-context"/"context.db"; db.parent.mkdir(parents=True); conn=sqlite3.connect(db); conn.execute("PRAGMA user_version=2"); conn.commit(); conn.close()
            st=shared_context.detect(root); self.assertEqual(st["version"],"0.2.0"); self.assertEqual(st["schema_version"],2); self.assertTrue(st["health_tool"]); self.assertTrue(st["compatible"])

    def test_old_or_unhealthy_bus_is_not_compatible(self):
        with tempfile.TemporaryDirectory() as home:
            target=Path(home)/"plugins"/"hermes-context-bus"; target.mkdir(parents=True); (target/"plugin.yaml").write_text('version: "0.1.0"\nprovides_tools: []\n')
            self.assertFalse(shared_context.detect(Path(home))["compatible"])

    def test_health_tool_must_be_declared_under_provides_tools(self):
        with tempfile.TemporaryDirectory() as home:
            target=Path(home)/"plugins"/"hermes-context-bus"; target.mkdir(parents=True)
            (target/"plugin.yaml").write_text(
                'name: hermes-context-bus\nversion: "0.2.0"\n'
                'not_tools:\n  - shared_context_health\nprovides_tools: []\n'
            )
            st=shared_context.detect(Path(home))
            self.assertFalse(st["health_tool"])
            self.assertFalse(st["compatible"])

    def test_install_requires_v02_health_and_replace_is_explicit(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as home:
            src=self._source(source,"0.1.0",False)
            with self.assertRaises(ValueError): shared_context.install_from_source(src,Path(home))
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as home:
            src=Path(source)
            (src/"plugin.yaml").write_text('name: lookalike-plugin\nversion: "0.2.0"\nprovides_tools:\n  - shared_context_health\n')
            with self.assertRaisesRegex(ValueError,"hermes-context-bus"):
                shared_context.install_from_source(src,Path(home))
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as home:
            src=self._source(source); target=Path(home)/"plugins"/"hermes-context-bus"; target.mkdir(parents=True); (target/"plugin.yaml").write_text('version: "0.1.0"\n')
            with self.assertRaisesRegex(ValueError,"replace"): shared_context.install_from_source(src,Path(home))
            self.assertTrue(shared_context.install_from_source(src,Path(home),replace=True)["compatible"])

    def test_replace_copy_failure_preserves_existing_install(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as home:
            src=self._source(source)
            target=Path(home)/"plugins"/"hermes-context-bus"
            target.mkdir(parents=True)
            (target/"plugin.yaml").write_text(MANIFEST)
            (target/"KEEP").write_text("old")
            def fail_copy(src_path,dst_path,*args,**kwargs):
                raise OSError("simulated copy failure")
            with patch.object(shared_context.shutil,"copytree",side_effect=fail_copy):
                with self.assertRaisesRegex(OSError,"simulated"):
                    shared_context.install_from_source(src,Path(home),replace=True)
            self.assertTrue((target/"KEEP").exists())
            self.assertTrue(shared_context.detect(Path(home))["compatible"])

    def test_rejects_symlinked_source_content(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as home:
            src=self._source(source)
            secret=Path(outside)/"secret.txt"; secret.write_text("do-not-copy")
            try:
                (src/"linked-secret").symlink_to(secret)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError,"symlink"):
                shared_context.install_from_source(src,Path(home))

    def test_rejects_symlinked_source_root(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as links, tempfile.TemporaryDirectory() as home:
            src=self._source(source)
            link=Path(links)/"bus"
            try:
                link.symlink_to(src, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError,"symlink"):
                shared_context.install_from_source(link,Path(home))

    def test_existing_symlinked_install_is_not_compatible(self):
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as home:
            ext=self._source(outside)
            plugins=Path(home)/"plugins"; plugins.mkdir()
            link=plugins/"hermes-context-bus"
            try:
                link.symlink_to(ext,target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            st=shared_context.detect(Path(home))
            self.assertTrue(st["installed"])
            self.assertTrue(st["symlinked"])
            self.assertFalse(st["compatible"])

    def test_reconcile_uses_hermes_cli_and_propagates_home(self):
        calls=[]
        class P: returncode=0; stdout=""; stderr=""
        def runner(cmd,**kwargs): calls.append((cmd,kwargs)); return P()
        with tempfile.TemporaryDirectory() as home:
            target=Path(home)/"plugins"/"hermes-context-bus"; target.mkdir(parents=True); (target/"plugin.yaml").write_text(MANIFEST)
            result=shared_context.reconcile_enabled(False,home=Path(home),runner=runner)
            self.assertTrue(result["changed"]); self.assertEqual(calls[0][0][1:3],["plugins","disable"]); self.assertEqual(calls[0][1]["env"]["HERMES_HOME"],home)

    def test_missing_hermes_cli_is_clean_error(self):
        with tempfile.TemporaryDirectory() as home:
            target=Path(home)/"plugins"/"hermes-context-bus"; target.mkdir(parents=True); (target/"plugin.yaml").write_text(MANIFEST)
            def runner(*a,**k): raise FileNotFoundError("hermes")
            with patch.object(shared_context.shutil,"which",return_value=None), self.assertRaisesRegex(RuntimeError,"not installed"):
                shared_context.reconcile_enabled(False,home=Path(home),runner=runner)
