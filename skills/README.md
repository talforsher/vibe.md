# Skills

This directory is the canonical home of every vibe.md skill. Each sub-directory is one skill:

```text
skills/
└── <skill-name>/
    ├── SKILL.md        # required: YAML frontmatter + instructions
    ├── scripts/        # optional: helper scripts the agent may run
    ├── references/     # optional: extra documentation loaded on demand
    └── assets/         # optional: templates, examples, data files
```

There are no published skills yet. The collection is ready for its first community contributions.

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md`. The directory name must match the `name` field.
2. Use lowercase kebab-case for the name, for example `git-workflow`.
3. Write a `description` that says what the skill does **and** when an agent should use it.
4. Keep every file the skill needs inside its own directory, and link to them with relative paths.
5. Validate your work:

   ```bash
   python3 scripts/validate-skills.py
   ```

6. Open a Pull Request. CI discovers and validates the new skill automatically.

A regular skill contribution only touches files inside `skills/<skill-name>/`. You never need to edit the installer, the validator, or CI to add a skill.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the complete format, a full example, and the review checklist.
