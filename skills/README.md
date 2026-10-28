# Skills

This directory is the canonical home of vibe.md skills and skill groups:

```text
skills/
├── _shared/
│   └── vibe/SKILL.md    # general router, included in every installation
├── gitly/
│   ├── README.md
│   ├── gitly-status/SKILL.md
│   └── gitly-save/SKILL.md
└── <skill-name>/        # standalone skills remain supported
    ├── SKILL.md        # required: YAML frontmatter + instructions
    ├── scripts/        # optional: helper scripts the agent may run
    ├── references/     # optional: extra documentation loaded on demand
    └── assets/         # optional: templates, examples, data files
```

Gitly contains twelve independently usable skills. Install the group with:

```bash
bash scripts/install.sh --group gitly --agent codex --project /path/to/project
```

This installs the `vibe` router and twelve `gitly-*` directories directly into
`.agents/skills/`. Each workflow has its own `SKILL.md` and bundled resources.
Use `--skill gitly-status` for just one workflow plus the router. Replace `codex`
with your agent's name to use its discovery directory.

The router uses the installed skill catalog and each skill's description, so
future groups work without editing a central routing table. Project-level
`AGENTS.md` files are not created or changed. See [Gitly](gitly/README.md) for usage.

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` or `skills/<group>/<skill-name>/SKILL.md`. The leaf directory must match `name`; names must be unique across the collection.
2. Use lowercase kebab-case for the name, for example `git-workflow`.
3. Write a `description` that says what the skill does **and** when an agent should use it.
4. Keep every file the skill needs inside its own directory, and link to them with relative paths. Set `metadata.collection: vibe.md` and `metadata.group: <group>` for routing.
5. Validate your work:

   ```bash
   python3 scripts/validate-skills.py
   ```

6. Open a Pull Request. CI discovers and validates the new skill automatically.

A regular contribution stays inside its skill or group directory. You never need
to edit the router, installer, validator, or CI to add a group. `_shared/` is
reserved for common skills automatically included in every installation.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the complete format, a full example, and the review checklist.
