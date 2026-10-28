# Security Policy

vibe.md distributes instructions and scripts that AI coding agents act on. A malicious or careless skill can cause real harm, so we take security reports seriously.

## Reporting a vulnerability

**Please do not report security issues in public issues, discussions, or Pull Requests.**

Report them privately through GitHub:

1. Go to the [Security tab](https://github.com/vibe-md/vibe.md/security) of the repository.
2. Click **Report a vulnerability** (or open a [new security advisory](https://github.com/vibe-md/vibe.md/security/advisories/new) directly).
3. Fill in the form. Only the maintainers can see your report.

This uses GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability).

### What to include

- The affected component: the installer, the validator, CI, or a specific skill (with its name).
- A description of the issue and its impact. What can an attacker do?
- Steps to reproduce, or a minimal proof of concept.
- The commit or version you tested.
- Any suggested fix, if you have one.

### What happens next

We aim to acknowledge reports within a few days, keep you informed while we investigate, and credit you in the advisory unless you prefer to remain anonymous. vibe.md is maintained by volunteers, so response times can vary.

## Scope

In scope:

- `scripts/install.sh`: for example path traversal, writes outside the target project, unsafe handling of downloads or temporary files.
- `scripts/validate-skills.py` and the GitHub Actions workflows.
- Skills in `skills/`: malicious instructions, hidden or destructive operations, credential exfiltration, prompt injection, or bundled scripts that do something other than what the skill documents.

Out of scope: vulnerabilities in the coding agents themselves (report those to their vendors) and issues that require an attacker who already controls your machine.

## Security expectations for contributed skills

Every skill must:

- **Contain no secrets.** No API keys, tokens, passwords, private URLs, or personal data.
- **Do what it says.** Bundled scripts must match the behavior documented in `SKILL.md`. No obfuscated code, encoded payloads, or hidden network calls.
- **Avoid destructive defaults.** Operations such as deleting files, force-pushing, rewriting history, or changing system configuration must be explicit, explained, and confirmed with the user.
- **Never escalate privileges.** Skills must not require `sudo` or modify files outside the project unless that is their clearly documented purpose.
- **Not download and execute remote code** (for example `curl ... | sh`) at run time.
- **Not ask agents to bypass safety controls**, ignore user instructions, or pre-approve shell access through `allowed-tools` without a clear reason.
- **Keep dependencies inside the skill or group.** A skill may use its own files and top-level group Markdown documents or `LICENSE`, which are included automatically on installation. Links to sibling workflows or outside the group are rejected. Symbolic links are rejected by the validator.

Maintainers review every new skill and every change to an existing skill before merging. Reviews reduce risk but cannot eliminate it.

## Malicious or unsafe skills

If you find a skill that looks malicious or unsafe, report it privately as described above. Maintainers may remove a skill immediately, without prior discussion, if it puts users at risk.

## Safe use of third-party skills

**Always review a skill before you install it.** This applies to vibe.md and to every other source of agent skills. A skill tells your agent what to do, and agents may run bundled scripts with your permissions.

- Read `SKILL.md` and every bundled script before installing. Use `--dry-run` to see exactly which files will be copied.
- Prefer installing from a local clone you have inspected over piping a remote script into your shell.
- Keep your agent's permission prompts enabled for shell commands.
- Re-review a skill when you update it.

The installer itself only copies files: it never runs a skill's scripts, never uses `sudo`, and refuses to write outside the target project.
