from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_footprint.cli import Change, Entry, _markdown_report, compare, snapshot


class AgentFootprintTest(unittest.TestCase):
    def test_snapshot_finds_content_mode_and_symlink_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            changed = root / "ignored.env"
            changed.write_text("before", encoding="utf-8")
            link = root / "current"
            link.symlink_to("ignored.env")
            before = snapshot(root, ())

            changed.write_text("after!", encoding="utf-8")
            changed.chmod(0o600)
            link.unlink()
            link.symlink_to("other.env")
            after = snapshot(root, ())

            changes = {change.path: change for change in compare(before, after)}
            self.assertEqual(changes["ignored.env"].status, "modified")
            self.assertIsNotNone(changes["ignored.env"].after)
            assert changes["ignored.env"].after is not None
            self.assertEqual(changes["ignored.env"].after.mode, "0600")
            self.assertEqual(changes["current"].status, "modified")

    def test_compare_classifies_add_and_delete(self) -> None:
        entry = Entry("file", 1, "0644", "hash")
        changes = compare({"old": entry}, {"new": entry})
        self.assertEqual(
            [(item.path, item.status) for item in changes],
            [("new", "added"), ("old", "deleted")],
        )

    def test_cli_reports_git_ignored_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
            command = [
                sys.executable,
                "-m",
                "agent_footprint",
                "--root",
                str(root),
                "--json",
                "--",
                sys.executable,
                "-c",
                "from pathlib import Path; Path('secret.txt').write_text('changed')",
            ]
            environment = os.environ.copy()
            source = str(Path(__file__).parents[1] / "src")
            environment["PYTHONPATH"] = (
                source + os.pathsep + environment.get("PYTHONPATH", "")
            )
            result = subprocess.run(
                command, check=False, capture_output=True, text=True, env=environment
            )
            report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(report["change_count"], 1)
            self.assertEqual(report["changes"][0]["path"], "secret.txt")

    def test_fail_on_change_uses_exit_three(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = [
                sys.executable,
                "-m",
                "agent_footprint",
                "--root",
                str(root),
                "--fail-on-change",
                "--",
                sys.executable,
                "-c",
                "open('new.txt', 'w').write('x')",
            ]
            environment = os.environ.copy()
            source = str(Path(__file__).parents[1] / "src")
            environment["PYTHONPATH"] = (
                source + os.pathsep + environment.get("PYTHONPATH", "")
            )
            result = subprocess.run(
                command, check=False, capture_output=True, text=True, env=environment
            )
            self.assertEqual(result.returncode, 3)

    def test_markdown_escapes_untrusted_paths_and_commands(self) -> None:
        entry = Entry("file", 1, "0644", "hash")
        changes = [Change("<img onerror=alert(1)>", "added", None, entry)]
        report: dict[str, object] = {
            "command": ["tool", "line\n<script>"],
            "root": "<root>",
            "exit_code": 0,
            "started_at": "now",
            "finished_at": "later",
            "change_count": 1,
        }
        rendered = _markdown_report(report, changes)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img ", rendered)
        self.assertIn("\\n&lt;script&gt;", rendered)


if __name__ == "__main__":
    unittest.main()
