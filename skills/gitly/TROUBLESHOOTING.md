# Troubleshooting

- **The skills do not appear.** Confirm the agent found the correct package in Downloads and completed its `INSTALL.md` plan in the currently open project. Restart/reload the agent, then invoke `gitly-setup` explicitly. Check [compatibility](COMPATIBILITY.md).
- **The agent cannot find the download.** Allow its request to read Downloads, or paste the package's full path into chat. The package does not need to be moved into the project.
- **The extracted folder looks empty.** Download the latest ZIP. It should contain a visible `gitly-install` folder with `INSTALL.md`, `skills`, and `shared`.
- **The project already has `.claude`, `.agents`, `.cursor`, or `.gitly`.** Merge folders rather than replacing them. If a `gitly-*` file already exists, compare it before updating. Never overwrite unrelated instructions.
- **Git is missing.** Ask `gitly-setup`; it will guide you to the official installer for your platform. Gitly itself needs no runtime.
- **GitHub is unavailable.** Install the official GitHub CLI and run its browser/device login yourself. Never paste a token into chat.
- **The project stopped working.** Ask `gitly-check` to inspect the symptom and propose the smallest relevant existing checks. A general breakage report never triggers restoration; ask explicitly to return to an earlier version when that is what you want.
- **Approval is requested again.** Repository state or the proposed action changed. This is intentional; inspect and approve a fresh plan.
- **A merge conflicts.** Gitly stops with both sides present. Decide the intended behavior before approving resolutions or an abort.
- **Preferences are malformed.** Do not overwrite the file. Ask `gitly-settings` to show the invalid fields and propose a reviewed repair.
- **Updating or removing Gitly.** Replace or remove only the twelve `gitly-*` skill folders (each includes its local contract). Preserve `.gitly/config.md` unless preferences should also be removed.

- **Using the terminal installer.** Run the vibe.md installer with `--group gitly`
  and the matching `--agent`. Identical copies are reused; differences stop before
  any write. Review changes before using `--force`.
- **Adding another group.** The existing `vibe` router is reused when identical.
  Other groups and `.gitly/config.md` are preserved.
- **Previously installed Gitly.** Old skill files point to a project-level contract
  and differ from the new packages. Back up any customizations, review the new
  files, then use the vibe.md installer with `--force` to replace only selected
  skills. Keep `.gitly/config.md`. Once all old Gitly skills have been updated,
  the obsolete project-level `.gitly/GITLY.md` can be removed.
