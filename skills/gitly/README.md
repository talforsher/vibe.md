# Gitly for vibe.md

Gitly helps a coding agent handle Git, project checks, recovery, and GitHub
workflows through everyday requests in English, Hebrew, or the user's language.
It is a set of instructions with no runtime, service, account, or bundled scripts.

## Install

From a local vibe.md checkout:

```bash
bash scripts/install.sh --skill gitly --agent codex --project /path/to/project --dry-run
bash scripts/install.sh --skill gitly --agent codex --project /path/to/project
```

Choose `claude-code`, `cursor`, `gemini`, or `copilot` instead of `codex` to use
another agent's installation directory. The installer copies this entire folder,
including the shared contract and every workflow reference.

Reload your agent as directed by the installer, then ask "Set up Gitly", "Save my
progress", or "Is everything backed up?" The entry skill is named `gitly`; the
twelve `gitly-*` workflows are internal references, not separately installed
commands. Agent discovery and activation should be checked in the chosen host.

## Requirements and behavior

- Git is required for version workflows. GitHub connection and sync also require
  GitHub CLI (`gh`), an appropriate account, and network access.
- Project checks use existing project tools and may execute code or create files.
  The agent reviews the commands and asks for approval before running them.
- Read-only status, history, and comparison do not require approval. Changes,
  authentication, and synchronization follow the shared contract's explicit
  approval protocol.
- Preferences live in the project's `.gitly/config.md`, when present. Installing
  this bundle does not create or change that file.
- The shared operating contract lives inside this skill at `references/GITLY.md`.
  No separate project-level `.gitly/GITLY.md` installation is needed.

To remove the bundle, delete the installed `gitly/` skill folder. Keep any
project preferences if you want to retain them.

## Source and adaptations

Source: [NirGeron98/Gitly](https://github.com/NirGeron98/Gitly), commit
`fe33bbae13552ed8973c6949b1d21e1ce2b746c9`.

This contribution packages the twelve original skills as reference documents
under one `gitly` entry skill, fitting vibe.md's self-contained installation
format. Each workflow's external shared-contract path was replaced with a link
to the bundled `GITLY.md`. The remaining workflow text and shared contract are
unchanged. The contribution uses vibe.md's [MIT license](LICENSE).

Gitly's guidance relies on the host agent following instructions; it is not an
executable security boundary.
