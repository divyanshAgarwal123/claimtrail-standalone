"""Handoff behavior, policy pinning and native Codex hook I/O."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "src/handoff.py"


@unittest.skipUnless(os.name == "posix", "handoff uses a POSIX workspace lock")
class HandoffTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name).resolve()
        self.source = self.repo / "work.txt"
        self.source.write_text("ok")
        self.policy = self.repo / "policy.json"
        self.spec = {
            "check_id": "fixture", "scope": ["work.txt"],
            "command": [sys.executable, "-c",
                        "from pathlib import Path; raise SystemExit(Path('work.txt').read_text() == 'fail')"],
        }
        self.policy.write_text(json.dumps(self.spec))
        self.state = self.repo / ".claimtrail"

    def command(self, action, code=0, env=None):
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), action, "--policy", str(self.policy)],
            cwd=self.repo, env={**os.environ, "CLAIMTRAIL_ALLOWED_ROOT": str(self.repo), **(env or {})},
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def hook(self, installed, event, **fields):
        handler = json.loads(Path(installed["hooks"]).read_text())["hooks"][event][-1]["hooks"][0]
        payload = {"hook_event_name": event, "cwd": str(self.repo), "session_id": "sample", "turn_id": "turn"}
        result = subprocess.run(shlex.split(handler["command"]), cwd=self.repo, text=True, capture_output=True,
                                input=json.dumps({**payload, **fields}), check=True)
        return json.loads(result.stdout)

    def test_missing_reused_and_stale(self):
        first = self.command("handoff")
        self.assertEqual(first["initial"]["status"], "missing")
        saved = (self.state / "receipt.json").read_bytes()
        self.assertEqual(self.command("handoff")["action"], "reused_receipt")
        self.assertEqual((self.state / "receipt.json").read_bytes(), saved)
        self.source.write_text("different")
        record = self.command("handoff")
        self.assertEqual(record["action"], "ran_configured_check")
        self.assertEqual(record["initial"]["changed_paths"], ["work.txt"])
        self.assertTrue(record["ready"])

    def test_failed_result_holds_without_rerun(self):
        self.source.write_text("fail")
        self.assertEqual(self.command("check", code=1)["result"]["status"], "failed")
        self.assertEqual(self.command("handoff", code=1)["action"], "held")

    def test_runtime_change_forces_a_new_check(self):
        self.command("check", env={"TZ": "UTC"})
        record = self.command("handoff", env={"TZ": "America/New_York"})
        self.assertEqual(record["initial"]["status"], "runtime_mismatch")
        self.assertEqual(record["action"], "ran_configured_check")

    def test_installer_preserves_existing_hooks_and_registers_once(self):
        hooks = self.repo / ".codex/hooks.json"
        hooks.parent.mkdir()
        hooks.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo existing"}]}]}}))
        self.command("install-codex")
        installed = self.command("install-codex")
        handlers = json.loads(hooks.read_text())["hooks"]["Stop"]
        self.assertEqual(len(handlers), 2)
        self.assertEqual(handlers[0]["hooks"][0]["command"], "echo existing")
        self.assertIn("additionalContext", self.hook(installed, "SessionStart")["hookSpecificOutput"])
        self.assertEqual(self.hook(installed, "Stop"), {})
        self.assertEqual(json.loads((self.state / "handoff.json").read_text())["trigger"], "Stop")
        self.spec["command"] = [sys.executable, "-c", "raise SystemExit(10)"]
        self.policy.write_text(json.dumps(self.spec))
        self.assertIn("policy changed", self.hook(installed, "Stop")["systemMessage"])

    def test_stop_requests_one_status_update_and_skips_plan_mode(self):
        installed = self.command("install-codex")
        self.assertEqual(self.hook(installed, "Stop", permission_mode="plan"), {})
        self.assertFalse(self.state.exists())
        self.source.write_text("fail")
        self.assertEqual(self.hook(installed, "Stop")["decision"], "block")
        self.assertNotIn("decision", self.hook(installed, "Stop", stop_hook_active=True))

    def test_corrupt_receipt_is_held_and_can_be_recaptured(self):
        self.command("check")
        (self.state / "receipt.json").write_text("{")
        self.assertEqual(self.command("handoff", code=1)["result"]["status"], "invalid")
        self.assertTrue(self.command("check")["ready"])

    def test_state_inside_scoped_root_requires_exclusion(self):
        self.spec["scope"] = ["."]
        self.policy.write_text(json.dumps(self.spec))
        self.assertIn("exclude .claimtrail", self.command("handoff", code=2)["result"]["reason"])
