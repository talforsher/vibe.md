# Security model

Gitly's safeguards are procedural instructions enforced only to the extent that the selected host agent follows them. Markdown cannot prevent an agent or user with terminal access from running other commands, changing the skills, fabricating approval, or bypassing Gitly entirely.

Every Gitly skill nevertheless requires the same sequence before mutation: inspect real state, show an action-specific plan with effects and recovery, obtain explicit approval, recheck relevant state, execute only the plan, verify, and summarize. State changes invalidate the approval. Native host approval interfaces are preferred; a plan-ID text response is the fallback.

The instructions prohibit force push, hard reset, destructive clean, automatic conflict resolution, guessed Git identity, silent branch switching, hidden pushes, and credential collection. Dynamic refs and paths must be validated, paths follow `--`, and repository content/output is untrusted data rather than instruction text.

## Limits

- There is no executable allowlist, fingerprint, lock, expiry service, or human-only authorization boundary.
- Hooks, filters, credential helpers, Git LFS, submodules, Git, and GitHub CLI may cause external effects that Markdown cannot sandbox.
- Concurrent agents can change state between checks. Skills require an immediate recheck but cannot lock the repository.
- Secret detection depends on the host agent's inspection and can miss credentials. Gitly never intentionally prints or stores secret values.
- Network operations can partially succeed. Fresh inspection is required before any retry.

Recovery remains conservative: restore checkpoints selected dirty paths, undo uses revert, pull is fast-forward-only, merge conflicts keep both sides, and destructive deletion is outside normal workflows.
