"""ZIP downloads must remain complete, reproducible, and independently installable."""

import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_packages", ROOT / "scripts/build-packages.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    def test_every_gitly_download_contains_complete_directly_usable_skills(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "downloads"
            manifest = builder.build_packages(ROOT / "skills", "gitly", output, "test-ref")
            self.assertEqual(len(manifest["skills"]), 13)
            self.assertIn("vibe", manifest["skills"])
            for agent, (_, destination) in builder.AGENTS.items():
                package = output / manifest["agents"][agent]["archive"]
                self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), manifest["agents"][agent]["sha256"])
                with zipfile.ZipFile(package) as archive:
                    self.assertIsNone(archive.testzip())
                    package_manifest = json.loads(archive.read("gitly-install/MANIFEST.json"))
                    self.assertEqual(package_manifest["destination"], destination)
                    self.assertEqual(package_manifest["source_ref"], "test-ref")
                    self.assertIn("Do not ask for another confirmation", archive.read("gitly-install/INSTALL.md").decode())
                    self.assertEqual(set(archive.namelist()), {
                        "gitly-install/INSTALL.md", "gitly-install/MANIFEST.json",
                        *("gitly-install/" + name for name in package_manifest["files"]),
                    })
                    project = Path(temporary) / agent
                    for name, digest in package_manifest["files"].items():
                        data = archive.read("gitly-install/" + name)
                        self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                        relative = Path(name).relative_to("skills")
                        source = ROOT / "skills" / ("_shared" if relative.parts[0] == "vibe" else "gitly") / relative
                        self.assertEqual(data, source.read_bytes())
                        target = project / destination / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                    self.assertEqual(len(list((project / destination).glob("*/SKILL.md"))), 13)
                    for name in manifest["skills"]:
                        if name != "vibe":
                            self.assertEqual((project / destination / name / "references/GITLY.md").read_bytes(),
                                             (ROOT / "skills/gitly/GITLY.md").read_bytes())
                    self.assertFalse((project / ".gitly").exists())

    def test_identical_inputs_produce_identical_archives_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            builder.build_packages(ROOT / "skills", "gitly", output, "test-ref")
            first = {p.name: p.read_bytes() for p in output.iterdir()}
            builder.build_packages(ROOT / "skills", "gitly", output, "test-ref")
            self.assertEqual(first, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_other_groups_work_and_unsafe_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            skills = base / "skills"
            shutil.copytree(ROOT / "tests/fixtures/valid/basic-skill", skills / "docs/basic-skill")
            script = skills / "docs/basic-skill/run.sh"
            script.write_text("#!/bin/sh\nexit 0\n")
            script.chmod(0o755)
            output = base / "downloads"
            manifest = builder.build_packages(skills, "docs", output, "test-ref")
            self.assertEqual(manifest["skills"], ["basic-skill"])
            with zipfile.ZipFile(output / "docs-codex.zip") as archive:
                self.assertEqual(archive.getinfo("docs-install/skills/basic-skill/run.sh").external_attr >> 16 & 0o777, 0o755)
            os.symlink("/etc/hosts", skills / "docs/basic-skill/hosts")
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                builder.build_packages(skills, "docs", output, "test-ref")
            with self.assertRaisesRegex(ValueError, "lowercase kebab-case"):
                builder.build_packages(skills, "../docs", output, "test-ref")


if __name__ == "__main__":
    unittest.main()
