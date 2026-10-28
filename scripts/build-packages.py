#!/usr/bin/env python3
"""Build reproducible, agent-guided ZIP downloads from a vibe.md skill group."""

import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = {
    "claude-code": ("Claude Code", ".claude/skills"),
    "codex": ("Codex", ".agents/skills"),
    "cursor": ("Cursor", ".cursor/skills"),
    "gemini": ("Gemini CLI", ".gemini/skills"),
    "copilot": ("GitHub Copilot", ".github/skills"),
}


def build_packages(skills_dir, group, output_dir, ref):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", group) or len(group) > 64:
        raise ValueError("group names must be lowercase kebab-case, up to 64 characters")
    group_dir = skills_dir / group
    if not group_dir.is_dir() or (group_dir / "SKILL.md").exists():
        raise ValueError("group not found: " + group)
    sources = sorted(group_dir.glob("*/SKILL.md")) + sorted((skills_dir / "_shared").glob("*/SKILL.md"))
    if not any(path.parent.parent == group_dir for path in sources):
        raise ValueError("group contains no skills: " + group)
    payload = {}
    modes = {}
    names = set()
    for entry in sources:
        skill = entry.parent
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill.name) or len(skill.name) > 64:
            raise ValueError("invalid skill name: " + skill.name)
        if skill.name in names:
            raise ValueError("duplicate skill name: " + skill.name)
        names.add(skill.name)
        if skill.is_symlink() or skill.parent.is_symlink():
            raise ValueError("symbolic links are not allowed: " + str(skill))
        for path in sorted(skill.rglob("*")):
            if path.is_symlink():
                raise ValueError("symbolic links are not allowed: " + str(path))
            if path.is_file():
                name = "skills/" + skill.name + "/" + path.relative_to(skill).as_posix()
                data = path.read_bytes()
                if path == entry and skill.parent == group_dir:
                    data = re.sub(rb"(\]\([ \t]*<?)\.\./", lambda match: match[1] + ("../" + group + "/").encode(), data)
                payload[name] = data
                modes[name] = 0o755 if path.stat().st_mode & 0o111 else 0o644

    resources = [path for path in sorted(group_dir.iterdir()) if not path.name.startswith(".")
                 and (path.suffix == ".md" or path.name == "LICENSE")]
    if resources and group in names:
        raise ValueError("group resources conflict with a skill of the same name: " + group)
    for path in resources:
        if path.is_symlink() or not path.is_file():
            raise ValueError("group resources must be regular files, without symbolic links: " + str(path))
        payload["skills/" + group + "/" + path.name] = path.read_bytes()

    output_dir.mkdir(parents=True, exist_ok=True)
    root = group + "-install"
    inventory = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())}
    manifest = {
        "group": group,
        "source_repository": "vibe-md/vibe.md",
        "source_ref": ref,
        "skills": sorted(names),
        "agents": {},
    }
    for agent, (label, destination) in AGENTS.items():
        guide = f"""# Install {group} from vibe.md for {label}

This package targets {label}. Stop if the currently open agent does not match.
Install only in the user's currently open project, never in this extracted folder.
The user's request to install this package authorizes copying missing files.

1. Read MANIFEST.json beside this file. Verify that the complete package contains
   exactly its listed skills and files, with matching SHA-256 hashes and no
   symbolic links. Required skills: {', '.join(sorted(names))}.
2. Inspect ALL destination directories at `{destination}/<directory>/` first,
   including the group resources directory `{destination}/{group}/` when present.
   Classify each complete directory as missing, byte-for-byte identical, or
   conflicting, including any extra destination files. If any directory conflicts,
   stop before writing anything and ask the user how to handle it. Preserve all
   unrelated skills and project files. Never overwrite a conflicting directory.
3. When every destination is missing or identical, create missing directories and
   copy the complete contents of each directory under `skills/` into its destination.
   Do not ask for another confirmation and do not rewrite identical directories.
   This includes the shared vibe router and the group's shared documents and license.
4. Verify every installed file against MANIFEST.json. Do not run bundled scripts,
   change Git history, authenticate, or edit AGENTS.md, CLAUDE.md, or preferences.
5. Report the installed skills. Remove only temporary extraction files you created;
   preserve the downloaded ZIP and any user-created extracted folder.
6. Tell the user to reload {label}, then ask for their desired workflow in ordinary
   language. Individual skills can also be
   invoked directly; the vibe router helps choose among installed workflows.

Follow each skill's documented prerequisites. Installing skills does not install
their tools, execute their workflows, or change existing project preferences.
"""
        package_manifest = {
            "group": group, "agent": agent, "destination": destination,
            "source_repository": manifest["source_repository"], "source_ref": ref,
            "skills": sorted(names), "files": inventory,
        }
        files = dict(payload)
        files["INSTALL.md"] = guide.encode()
        files["MANIFEST.json"] = (json.dumps(package_manifest, indent=2, sort_keys=True) + "\n").encode()
        filename = group + "-" + agent + ".zip"
        target = output_dir / filename
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(root + "/" + name, (2026, 1, 1, 0, 0, 0))
                info.external_attr = (stat.S_IFREG | modes.get(name, 0o644)) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        manifest["agents"][agent] = {
            "name": label, "skills_dir": destination, "archive": filename,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    (output_dir / (group + "-manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True)
    parser.add_argument("--skills-dir", type=Path, default=ROOT / "skills")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/downloads")
    parser.add_argument("--ref", help="Published source commit used by terminal installation")
    args = parser.parse_args()
    ref = args.ref
    if not ref:
        ref = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    try:
        manifest = build_packages(args.skills_dir, args.group, args.output_dir, ref)
    except ValueError as error:
        parser.error(str(error))
    print("Built {} packages for {} skills in {}".format(len(AGENTS), len(manifest["skills"]), args.output_dir))


if __name__ == "__main__":
    main()
