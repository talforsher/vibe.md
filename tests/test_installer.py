"""Tests for scripts/install.sh.

Every test runs inside its own temporary directory with HOME and TMPDIR pointed
there, so nothing is ever installed into a real agent configuration. Local
tests need no network access. Set VIBE_MD_INTEGRATION=1 to also run the tests
that download the real repository from GitHub.

Run with: python3 -m unittest discover -s tests -v
"""

import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER = REPO_ROOT / "scripts" / "install.sh"
VALID = REPO_ROOT / "tests" / "fixtures" / "valid"

AGENT_DIRS = {
    "claude-code": ".claude/skills",
    "codex": ".agents/skills",
    "cursor": ".cursor/skills",
    "gemini": ".gemini/skills",
    "copilot": ".github/skills",
}


def snapshot(root):
    """Every path under root, relative to root."""
    paths = set()
    for current, dirs, files in os.walk(str(root)):
        for name in dirs + files:
            paths.add(os.path.relpath(os.path.join(current, name), str(root)))
    return paths


def tree(root):
    """Map of relative file path -> bytes, for comparing directory contents."""
    root = Path(root)
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


class InstallerTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="vibe md test "))  # contains spaces on purpose
        self.home = self.root / "home"
        self.tmpdir = self.root / "tmp"
        self.project = self.root / "my project"
        for path in (self.home, self.tmpdir, self.project):
            path.mkdir()

    def tearDown(self):
        for current, dirs, _ in os.walk(str(self.root)):
            for name in dirs:
                os.chmod(os.path.join(current, name), 0o755)
        shutil.rmtree(str(self.root))

    def run_installer(self, *args, script=INSTALLER, cwd=None, env_extra=None, stdin_script=False):
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "TMPDIR": str(self.tmpdir),
            "LC_ALL": "C",
        }
        if env_extra:
            env.update(env_extra)
        if stdin_script:
            command = ["bash", "-s", "--"] + list(args)
            stdin = Path(script).read_text()
        else:
            command = ["bash", str(script)] + list(args)
            stdin = None
        return subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(cwd or self.project),
        )

    def install(self, skill="basic-skill", agent="claude-code", *extra, skills_dir=VALID):
        return self.run_installer(
            "--skill", skill, "--agent", agent, "--project", str(self.project),
            "--skills-dir", str(skills_dir), *extra
        )


class CommandLineTests(InstallerTestCase):
    def test_help(self):
        result = self.run_installer("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        for agent, directory in AGENT_DIRS.items():
            self.assertIn(agent, result.stdout)
            self.assertIn(directory, result.stdout)

    def test_unknown_option(self):
        result = self.run_installer("--bogus")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option", result.stderr)

    def test_missing_skill_and_agent(self):
        result = self.run_installer("--agent", "codex")
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing --skill", result.stderr)
        result = self.run_installer("--skill", "basic-skill")
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing --agent", result.stderr)

    def test_option_without_value(self):
        result = self.run_installer("--skill")
        self.assertEqual(result.returncode, 2)
        self.assertIn("needs a value", result.stderr)

    def test_equals_syntax(self):
        result = self.run_installer(
            "--skill=basic-skill", "--agent=codex", "--project=" + str(self.project),
            "--skills-dir=" + str(VALID),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".agents/skills/basic-skill/SKILL.md").is_file())

    def test_unknown_agent(self):
        result = self.install(agent="notepad")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown agent 'notepad'", result.stderr)
        self.assertEqual(snapshot(self.project), set())

    def test_unknown_skill(self):
        result = self.install(skill="does-not-exist")
        self.assertEqual(result.returncode, 1)
        self.assertIn("skill 'does-not-exist' was not found", result.stderr)
        self.assertEqual(snapshot(self.project), set())

    def test_path_traversal_in_skill_name_is_rejected(self):
        for name in ["../basic-skill", "basic-skill/..", "/etc", "Basic-Skill", "a b", ".hidden"]:
            with self.subTest(name=name):
                result = self.install(skill=name)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("invalid skill name", result.stderr)
        self.assertEqual(snapshot(self.project), set())

    def test_invalid_ref_is_rejected(self):
        result = self.run_installer("--list", "--ref", "../../evil")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid --ref", result.stderr)

    def test_missing_project_directory(self):
        result = self.run_installer(
            "--skill", "basic-skill", "--agent", "codex", "--skills-dir", str(VALID),
            "--project", str(self.root / "nope"),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("project directory not found", result.stderr)


class ListTests(InstallerTestCase):
    def test_list_empty_collection(self):
        empty = self.root / "empty skills"
        empty.mkdir()
        (empty / "README.md").write_text("# Skills\n")
        result = self.run_installer("--list", "--skills-dir", str(empty))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No skills are available yet.", result.stdout)

    def test_list_shows_skills_and_descriptions(self):
        result = self.run_installer("--list", "--skills-dir", str(VALID))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("basic-skill", result.stdout)
        self.assertIn("A minimal test skill", result.stdout)
        # Folded YAML description (description: >) is read too.
        self.assertIn("A test skill with bundled scripts", result.stdout)

    def test_repository_catalog_never_lists_test_fixtures(self):
        result = self.run_installer("--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        for fixture in ("basic-skill", "bundled-resources"):
            self.assertNotIn(fixture, result.stdout)


class InstallTests(InstallerTestCase):
    def test_every_agent_destination(self):
        for agent, directory in AGENT_DIRS.items():
            with self.subTest(agent=agent):
                result = self.install("basic-skill", agent)
                self.assertEqual(result.returncode, 0, result.stderr)
                dest = self.project / directory / "basic-skill"
                self.assertEqual(tree(dest), tree(VALID / "basic-skill"))
                self.assertIn(str(dest), result.stdout)

    def test_runs_in_current_directory_by_default(self):
        result = self.run_installer(
            "--skill", "basic-skill", "--agent", "cursor", "--skills-dir", str(VALID),
            cwd=self.project,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".cursor/skills/basic-skill/SKILL.md").is_file())

    def test_bundled_resources_are_installed_but_not_executed(self):
        skills = self.root / "skills"
        skill = skills / "runs-nothing"
        shutil.copytree(str(VALID / "bundled-resources"), str(skill))
        text = (skill / "SKILL.md").read_text().replace("name: bundled-resources", "name: runs-nothing")
        (skill / "SKILL.md").write_text(text)
        marker = self.root / "script-was-executed"
        script = skill / "scripts" / "hello.sh"
        script.write_text("#!/usr/bin/env bash\ntouch '{}'\n".format(marker))
        script.chmod(0o755)

        result = self.install("runs-nothing", "codex", skills_dir=skills)
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.project / ".agents/skills/runs-nothing"
        self.assertEqual(tree(dest), tree(skill))
        self.assertTrue(os.access(str(dest / "scripts/hello.sh"), os.X_OK))
        self.assertTrue((dest / "references/guide.md").is_file())
        self.assertTrue((dest / "assets/template.txt").is_file())
        self.assertFalse(marker.exists(), "the installer must never run bundled scripts")

    def test_identical_reinstall_is_a_no_op(self):
        self.assertEqual(self.install().returncode, 0)
        before = tree(self.project)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already installed", result.stdout)
        self.assertEqual(tree(self.project), before)

    def test_conflicting_skill_is_not_overwritten(self):
        dest = self.project / ".claude/skills/basic-skill"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("my own skill\n")
        (dest / "notes.txt").write_text("keep me\n")
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("already exists and differs", result.stderr)
        self.assertIn("--force", result.stderr)
        self.assertEqual((dest / "SKILL.md").read_text(), "my own skill\n")
        self.assertEqual((dest / "notes.txt").read_text(), "keep me\n")

    def test_force_replaces_conflicting_skill(self):
        dest = self.project / ".claude/skills/basic-skill"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("old\n")
        (dest / "stale.txt").write_text("stale\n")
        result = self.install("basic-skill", "claude-code", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Replaced", result.stdout)
        self.assertEqual(tree(dest), tree(VALID / "basic-skill"))

    def test_existing_file_at_destination_is_a_conflict(self):
        skills_root = self.project / ".claude/skills"
        skills_root.mkdir(parents=True)
        (skills_root / "basic-skill").write_text("a file, not a skill\n")
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertEqual((skills_root / "basic-skill").read_text(), "a file, not a skill\n")

    def test_other_skills_are_untouched(self):
        other = self.project / ".claude/skills/someone-elses-skill"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("theirs\n")
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual((other / "SKILL.md").read_text(), "theirs\n")

    def test_dry_run_writes_nothing(self):
        result = self.install("bundled-resources", "gemini", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run", result.stdout)
        self.assertIn("scripts/hello.sh", result.stdout)
        self.assertIn(".gemini/skills/bundled-resources", result.stdout)
        self.assertEqual(snapshot(self.project), set())

    def test_dry_run_reports_conflicts(self):
        dest = self.project / ".github/skills/basic-skill"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("different\n")
        result = self.install("basic-skill", "copilot", "--dry-run")
        self.assertEqual(result.returncode, 1)
        self.assertIn("already exists", result.stderr)

    def test_paths_with_spaces(self):
        skills = self.root / "skills with spaces"
        shutil.copytree(str(VALID / "basic-skill"), str(skills / "basic-skill"))
        project = self.root / "project with   spaces"
        project.mkdir()
        result = self.run_installer(
            "--skill", "basic-skill", "--agent", "claude-code",
            "--project", str(project), "--skills-dir", str(skills),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / ".claude/skills/basic-skill/SKILL.md").is_file())

    def test_no_writes_outside_destination(self):
        before = snapshot(self.root)
        self.assertEqual(self.install("bundled-resources", "codex").returncode, 0)
        created = snapshot(self.root) - before
        project = os.path.relpath(str(self.project), str(self.root))
        expected_prefix = os.path.join(project, ".agents")
        for path in created:
            self.assertTrue(path.startswith(expected_prefix), "unexpected write: " + path)
        self.assertEqual(snapshot(self.home), set())
        self.assertEqual(snapshot(self.tmpdir), set())

    def test_symlinked_agent_directory_outside_project_is_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        os.symlink(str(outside), str(self.project / ".claude"))
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the project", result.stderr)
        self.assertEqual(snapshot(outside), set())

    def test_skill_containing_symlink_is_refused(self):
        skills = self.root / "skills"
        shutil.copytree(str(VALID / "basic-skill"), str(skills / "basic-skill"))
        os.symlink("/etc/hosts", str(skills / "basic-skill" / "hosts"))
        result = self.install(skills_dir=skills)
        self.assertEqual(result.returncode, 1)
        self.assertIn("symbolic links", result.stderr)
        self.assertEqual(snapshot(self.project), set())

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "permissions are not enforced for root")
    def test_failed_installation_leaves_nothing_behind(self):
        agent_dir = self.project / ".claude"
        skills_root = agent_dir / "skills"
        skills_root.mkdir(parents=True)
        agent_dir.chmod(0o555)  # staging directory cannot be created
        result = self.install()
        agent_dir.chmod(0o755)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(snapshot(agent_dir), {"skills"})

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "permissions are not enforced for root")
    def test_failed_move_leaves_no_partial_skill(self):
        skills_root = self.project / ".claude/skills"
        skills_root.mkdir(parents=True)
        skills_root.chmod(0o555)  # final move into place fails
        result = self.install()
        skills_root.chmod(0o755)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(snapshot(skills_root), set())
        self.assertEqual(snapshot(self.project / ".claude"), {"skills"})


class RemoteInstallTests(InstallerTestCase):
    """The installer run on its own downloads the collection. A local archive stands in for GitHub."""

    def setUp(self):
        super().setUp()
        self.lonely_script = self.root / "downloaded" / "install.sh"
        self.lonely_script.parent.mkdir()
        shutil.copy(str(INSTALLER), str(self.lonely_script))
        self.archive = self.root / "vibe.md-main.tar.gz"
        source = self.root / "archive-src" / "vibe.md-main"
        shutil.copytree(str(VALID), str(source / "skills"))
        with tarfile.open(str(self.archive), "w:gz") as tar:
            tar.add(str(source), arcname="vibe.md-main")
        self.env = {"VIBE_MD_ARCHIVE_URL": self.archive.as_uri()}

    def test_remote_list(self):
        result = self.run_installer("--list", script=self.lonely_script, env_extra=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("bundled-resources", result.stdout)
        self.assertEqual(snapshot(self.tmpdir), set(), "temporary download was not cleaned up")

    def test_remote_install_copies_complete_skill(self):
        result = self.run_installer(
            "--skill", "bundled-resources", "--agent", "codex", "--project", str(self.project),
            script=self.lonely_script, env_extra=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.project / ".agents/skills/bundled-resources"
        self.assertEqual(tree(dest), tree(VALID / "bundled-resources"))
        self.assertEqual(snapshot(self.tmpdir), set())

    def test_piped_install(self):
        """Equivalent of: curl -fsSL .../install.sh | bash -s -- --skill ... --agent ..."""
        result = self.run_installer(
            "--skill", "basic-skill", "--agent", "cursor",
            script=self.lonely_script, env_extra=self.env, stdin_script=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".cursor/skills/basic-skill/SKILL.md").is_file())
        self.assertEqual(snapshot(self.tmpdir), set())

    def test_failed_download(self):
        env = {"VIBE_MD_ARCHIVE_URL": (self.root / "missing.tar.gz").as_uri()}
        result = self.run_installer(
            "--skill", "basic-skill", "--agent", "codex", script=self.lonely_script, env_extra=env,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not download", result.stderr)
        self.assertEqual(snapshot(self.project), set())
        self.assertEqual(snapshot(self.tmpdir), set())

    def test_corrupt_download(self):
        bad = self.root / "bad.tar.gz"
        bad.write_text("this is not an archive")
        result = self.run_installer(
            "--list", script=self.lonely_script, env_extra={"VIBE_MD_ARCHIVE_URL": bad.as_uri()},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not be unpacked", result.stderr)
        self.assertEqual(snapshot(self.tmpdir), set())

    def test_archive_without_skills_directory(self):
        other = self.root / "other.tar.gz"
        src = self.root / "other-src" / "something-else"
        src.mkdir(parents=True)
        (src / "README.md").write_text("not vibe.md\n")
        with tarfile.open(str(other), "w:gz") as tar:
            tar.add(str(src), arcname="something-else")
        result = self.run_installer(
            "--list", script=self.lonely_script, env_extra={"VIBE_MD_ARCHIVE_URL": other.as_uri()},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not look like the vibe.md repository", result.stderr)


@unittest.skipUnless(os.environ.get("VIBE_MD_INTEGRATION") == "1", "set VIBE_MD_INTEGRATION=1 to run")
class GitHubIntegrationTests(InstallerTestCase):
    """Downloads the real repository from GitHub. Requires network access."""

    def test_remote_list_from_github(self):
        lonely = self.root / "install.sh"
        shutil.copy(str(INSTALLER), str(lonely))
        result = self.run_installer("--list", script=lonely)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(self.tmpdir), set())

    def test_remote_unknown_skill_from_github(self):
        lonely = self.root / "install.sh"
        shutil.copy(str(INSTALLER), str(lonely))
        result = self.run_installer("--skill", "no-such-skill-xyz", "--agent", "codex", script=lonely)
        self.assertEqual(result.returncode, 1)
        self.assertIn("was not found", result.stderr)
        self.assertEqual(snapshot(self.project), set())


if __name__ == "__main__":
    unittest.main()
