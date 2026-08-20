# `.claude/` — Claude Code project configuration

This directory holds the project's Claude Code / AI-collaboration configuration. Following the JOLT_Report
convention, the **shared conventions are committed** and the **personal / runtime / vendored parts are gitignored**
(see the root `.gitignore`).

## Committed (shared with the team)

| Path | What it is |
|------|------------|
| `rules/code-style.md` | Python style, naming, comments-in-English, sub-project independence. Imported by `CLAUDE.md`. |
| `rules/naming.md` | Data / file / directory / preset naming conventions. Imported by `CLAUDE.md`. |
| `rules/git-workflow.md` | Versioning (SemVer on `dcpredictor`), commits, branches, push consent, changelogs. Imported by `CLAUDE.md`. |
| `rules/housekeeping.md` | Temp/archive zones, archive-over-delete, OneDrive notes. Imported by `CLAUDE.md`. |
| `README.md` | This file. |

The root `CLAUDE.md` composes itself from these rule files via `@import`, so editing a rule here changes the
project-wide convention.

## Gitignored (personal / runtime / vendored)

- `settings.local.json` — machine-local Claude Code settings.
- `sessions/`, `worktrees/`, `agent-memory/` — runtime state.
- `skills/` — vendored third-party skills (e.g. `code-review-skill-main`); large and externally maintained.
