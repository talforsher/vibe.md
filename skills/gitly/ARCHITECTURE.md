# Skills-only architecture

```text
Natural-language request
          │
          ▼
  Host-native skill discovery
          │
          ├──► gitly-* / SKILL.md (one workflow)
          │            │
          │            └──► <skill>/references/GITLY.md (shared safety + config contract)
          │
          ▼
 Agent read-only inspection through its native terminal/tools
          │
          ▼
 Plain-language plan → explicit user approval → fresh state recheck
          │
          ▼
 Native Git / GitHub CLI action → verification → summary
```

Gitly has no execution layer. The host agent reads one relevant skill and the shared contract, then uses the terminal/tool permissions it already has. Skills are independent by responsibility and coordinate only at explicit workflow boundaries.

Project preferences live in `.gitly/config.md` only after the user approves a settings change. Missing configuration means defaults: local saves, five history items, private GitHub visibility, automatic response language, and confirmation always required. The file contains no credentials or machine-specific data.

Canonical sources live in `skills/gitly/` in the vibe.md skills repository. Each
workflow is a complete skill directory, including its local operating contract.
The group-level `GITLY.md` is the maintenance source; tests require every bundled
copy to match it. The common `skills/_shared/vibe/` router is installed with the
group and discovers workflows from installed metadata.

`bash scripts/install.sh --group gitly --agent <agent>` installs all twelve
workflows and the router. `--skill gitly-status` installs just that workflow and
the router. Terminal downloads come exclusively from vibe-md/vibe.md.

`python3 scripts/build-packages.py --group gitly` generates agent-specific,
reproducible ZIPs and a download manifest. Every ZIP includes `gitly-install/`
with `INSTALL.md`, a hashed `MANIFEST.json`, and all thirteen complete skill
folders. The frontend hosts those generated artifacts and the Gitly page inside
the vibe.md website. There is no dependency on a sibling Gitly checkout or the
old Gitly repository during installation or operation.
