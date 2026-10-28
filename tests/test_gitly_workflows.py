from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=check)


class NativeGitWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        git(self.root, "init", "--initial-branch=main")
        git(self.root, "config", "user.name", "Gitly Test")
        git(self.root, "config", "user.email", "gitly@example.invalid")
        (self.root / "app.txt").write_text("working login\n", encoding="utf-8")
        git(self.root, "add", "--", "app.txt")
        git(self.root, "commit", "-m", "Working login")

    def tearDown(self):
        self.temporary.cleanup()

    def test_save_history_and_compare_commands_preserve_unselected_work(self):
        first = git(self.root, "rev-parse", "HEAD").stdout.strip()
        (self.root / "app.txt").write_text("working login and dashboard\n", encoding="utf-8")
        (self.root / "notes.txt").write_text("not part of this save\n", encoding="utf-8")
        git(self.root, "add", "--", "app.txt")
        git(self.root, "diff", "--cached", "--check")
        git(self.root, "commit", "-m", "Add dashboard", "--", "app.txt")
        history = git(self.root, "log", "--format=%H%x1f%aI%x1f%s", "-2").stdout
        comparison = git(self.root, "diff", "--name-status", first, "HEAD").stdout
        status = git(self.root, "status", "--porcelain").stdout
        self.assertIn("Add dashboard", history)
        self.assertIn("M\tapp.txt", comparison)
        self.assertIn("?? notes.txt", status)

    def test_restore_checkpoint_command_is_recoverable(self):
        old = git(self.root, "rev-parse", "HEAD").stdout.strip()
        (self.root / "app.txt").write_text("new unsaved experiment\n", encoding="utf-8")
        git(self.root, "stash", "push", "--include-untracked", "-m", "Gitly restore checkpoint", "--", "app.txt")
        self.assertIn("Gitly restore checkpoint", git(self.root, "stash", "list").stdout)
        git(self.root, "restore", f"--source={old}", "--worktree", "--", "app.txt")
        self.assertEqual((self.root / "app.txt").read_text(), "working login\n")

    def test_merge_conflict_preserves_both_sides(self):
        git(self.root, "switch", "-c", "experiment")
        (self.root / "app.txt").write_text("experiment version\n", encoding="utf-8")
        git(self.root, "commit", "-am", "Experiment")
        git(self.root, "switch", "main")
        (self.root / "app.txt").write_text("main version\n", encoding="utf-8")
        git(self.root, "commit", "-am", "Main change")
        result = git(self.root, "merge", "--no-edit", "--", "experiment", check=False)
        self.assertNotEqual(result.returncode, 0)
        content = (self.root / "app.txt").read_text()
        self.assertIn("main version", content)
        self.assertIn("experiment version", content)
        self.assertTrue((self.root / ".git/MERGE_HEAD").exists())

    def test_project_preferences_persist_as_plain_text(self):
        config = self.root / ".gitly/config.md"
        config.parent.mkdir()
        config.write_text("version: 1\nsave_destination: local\nhistory_length: 10\ngithub_visibility: private\nlanguage: he\nconfirmation: always\n", encoding="utf-8")
        reopened = config.read_text(encoding="utf-8")
        self.assertIn("history_length: 10", reopened)
        self.assertIn("language: he", reopened)
        self.assertNotIn("token", reopened.casefold())


if __name__ == "__main__":
    unittest.main()
