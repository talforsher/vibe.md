# Gitly

Twelve independently discoverable skills for Git, project checks, recovery, and
GitHub workflows, with everyday English and Hebrew examples.

## Install the group

From a vibe.md checkout:

```bash
bash scripts/install.sh --group gitly --agent codex --project /path/to/project --dry-run
bash scripts/install.sh --group gitly --agent codex --project /path/to/project
```

Use `claude-code`, `cursor`, `gemini`, or `copilot` for another agent. Installation
places the shared `vibe` router and all twelve `gitly-*` skill directories directly
in the chosen agent's skills directory. Each has its own `SKILL.md`, local contract,
and license. No project-level `AGENTS.md` or `.gitly/GITLY.md` is needed.

After the reload steps printed by the installer, say "Set up Gitly", "Save my
progress", or "Is everything backed up?" You can also select an individual skill
through your agent's skill UI, such as `$gitly-status` in Codex, or use `$vibe`
when you want the router to choose. Automatic activation remains the host agent's
decision.

To install only one workflow with the shared router:

```bash
bash scripts/install.sh --skill gitly-status --agent codex --project /path/to/project
```

## Included skills

| Skill | Purpose |
| --- | --- |
| `gitly-setup` | Prepare Git, local identity, and ignore rules |
| `gitly-status` | Explain saved, unsaved, online, and at-risk work |
| `gitly-check` | Investigate project health and run approved existing checks |
| `gitly-save` | Save reviewed changes as a local commit |
| `gitly-history` | Find previous versions |
| `gitly-compare` | Explain changes between versions |
| `gitly-restore` | Recover files or undo commits after explicit recovery intent |
| `gitly-branches` | Create and switch safe experiments |
| `gitly-merge` | Combine work without guessing through conflicts |
| `gitly-github-connect` | Authenticate, create a repository, or link a remote |
| `gitly-sync` | Fetch, fast-forward pull, or push without force |
| `gitly-settings` | Read or update project preferences |

## Requirements

Git is required for version workflows. GitHub connection and sync also require
GitHub CLI (`gh`), an appropriate account, and network access. Project checks use
the project's existing tools. Changes and checks follow the bundled contract's
approval rules; read-only status, history, and comparison need no approval.

Preferences stay in the project's `.gitly/config.md`, if present. Missing
preferences use defaults without creating a file. Installing skills does not
modify project configuration or run Gitly workflows.

Remove installed `gitly-*` directories to remove the group. Keep `vibe/` if other
groups use it, and keep project preferences if you want to retain them.

## Source

Adapted from [NirGeron98/Gitly](https://github.com/NirGeron98/Gitly), commit
`fe33bbae13552ed8973c6949b1d21e1ce2b746c9`. Workflow instructions are preserved,
with their shared-contract paths changed to local relative links and attribution,
group, and license metadata added. Every skill carries an unchanged copy of the
shared contract, so it can also be installed independently. This contribution
uses vibe.md's [MIT license](LICENSE).

Gitly is agent guidance, not an executable security boundary.
