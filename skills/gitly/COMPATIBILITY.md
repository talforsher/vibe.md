# Agent compatibility

The notes below retain the original Gitly compatibility history. Historical UI
checks do not establish fresh UI behavior after migration. Current vibe.md
installation is covered by the repository tests; live discovery and routing in
each host still require verification.

Verified against official documentation available on 2026-10-23.

| Host | ZIP destination | Discovery | Invocation notes |
| --- | --- | --- | --- |
| Claude Code | `.claude/skills/gitly-*/SKILL.md` | Native project skills | Automatic relevance or `/gitly-save` style invocation |
| Codex | `.agents/skills/gitly-*/SKILL.md` | Open Agent Skills project discovery | Automatic relevance or explicit `$gitly-save` where supported |
| Cursor | `.cursor/skills/gitly-*/SKILL.md` | Native project Agent Skills | Automatic relevance, `/gitly-save`, or `@gitly-save` |

Sources: [Claude Code skills](https://code.claude.com/docs/en/skills), [OpenAI Agent Skills](https://developers.openai.com/api/docs/guides/tools-skills), and [Cursor skills](https://cursor.com/help/customization/skills).

Cursor also discovers compatible `.claude/skills` and `.agents/skills` folders. If Gitly is already installed for Claude Code or Codex in the same project, do not also copy the Cursor ZIP; Cursor can use the existing skills and this avoids duplicate names. When two agents genuinely need separate roots, generated definitions are identical, but updates must be applied consistently.

Native question and confirmation UI varies by host, version, and mode. All twelve skills read the shared contract, which prefers an available, permitted structured question tool for clarification and choices, with a numbered or free-text chat fallback. Tool names and availability are not portable across hosts; Gitly does not switch modes to obtain a question UI. Clarification choices do not approve actions, and a clarification-only tool must not be repurposed for approval. Every skill supports a clear text approval fallback tied to the current displayed plan. This is workflow guidance, not cryptographic authorization.

The shared question policy explicitly covers all three hosts: Codex uses `request_user_input` or `request_user_input_async` when available and allowed; Claude Code uses `AskUserQuestion`; Cursor uses its built-in **Ask questions** tool under the name exposed in the session. Host tool definitions remain authoritative. See [Claude Code's tool reference](https://code.claude.com/docs/en/tools-reference#askuserquestion-tool-behavior) and [Cursor's Ask questions documentation](https://cursor.com/docs/agent/overview#ask-questions). These question-tool references were checked on 2026-10-25; live UI behavior still needs validation in each host/mode.

## Validation matrix

| Capability | Automated | Still needs live validation |
| --- | --- | --- |
| Twelve manifests, metadata, safety sections, shared references | Yes | Automatic routing quality in each host |
| Claude/Codex/Cursor ZIP contents and destination mapping | Yes | Agent-guided installation in each host |
| No runtime/installer in downloads | Yes | Host terminal permission presentation |
| Settings schema and scenario coverage | Yes | Cross-chat behavior in each host |
| Structured questions and chat fallback | Shared instructions only | Tool availability, choice rendering, and replies in each host/mode |
| Website build and download availability | Yes | Full visual/device review |
| Git workflow guidance against disposable repositories | Static/scenario validation | Real agent execution and judgment |
| GitHub authentication | Documentation only | Browser login, SSO, repository creation, protected branches |

## Question UI verification — 2026-10-25

| Check | Result | Scope |
| --- | --- | --- |
| Codex question UI in the current conversation | Passed | User confirmed the options were selectable and the selected answer was received; fresh IDE skill discovery was not tested |
| Claude Code interactive CLI with the installed `gitly-settings` skill | Passed | Skill loaded the shared contract, displayed Hebrew choices, and received the selected answer; no preference file was written |
| Claude Code fallback without `AskUserQuestion` | Passed | The same installed skill explained the choices in Hebrew chat and requested a free-text choice; no preference file was written |
| Cursor native question UI | Not verified | Desktop automation could not start because the Computer Use client and server versions differ; Cursor's agent CLI was unavailable |
| All three ZIP packages and terminal installations | Passed | Archive integrity, exact source contents, all twelve relative shared-contract references, and repeat installation without rewriting files |
| Project checks | Passed | All 19 Python tests, package verification, website lint, typecheck, and production build |

The Claude Code check used a disposable project and read/question tools. It verifies the CLI question flow, not the Claude Code IDE extension. Completing the remaining visual checks requires relaunching ChatGPT to update the Computer Use client, then testing fresh installed skills in each IDE. These results do not establish native question rendering in every host or mode.

## vibe.md installation

The universal installer and package builder support `claude-code`, `codex`,
`cursor`, `gemini`, and `copilot`. Every destination is flat: thirteen directly discoverable
skill directories, including `vibe`, plus one `gitly/` documents directory. ZIPs
contain the same prepared layout.
The three original hosts retain their skill names and workflows. Gemini and
Copilot have installation coverage, not live Gitly workflow certification.
