> Tidiness and local-storage conventions — referenced from the root `CLAUDE.md` "## Housekeeping" section via `@import`.
> Editing here = editing the temp-file cleanup / archiving conventions for the whole project (committed with `.claude/`).

> This file governs **project tidiness and where files land**. For Python identifiers / one-off script naming see
> `code-style.md`; for data / directory naming see `naming.md`; for branch / commit / changelog see `git-workflow.md`.

### Temporary files: zones and cleanup

| Zone | Purpose | In git | Cleanup policy |
|------|---------|--------|----------------|
| `tmp/` (create on demand) | one-off scratch: logs, intermediate CSVs, debug figures, `_tmp_*.py` | No | clean after use |

- **Keep the repository root clean**: do not drop one-off scripts, logs, or env dumps directly in the root. They
  belong in `tmp/`.
- **This repo has no `archive/` zone** — it tracks only a small code + docs core, so superseded files are removed
  in a normal commit (git history is the archive). Retired artefacts that must stay on disk go to the sibling
  workspace archive (`../duty-cycle-predictor-workspace/archive/`).

### Data and large files

- Sample GPS data lives under `tests/data/<REG>/` and is **never committed** (gitignored; only the README is
  tracked). Generated results, HTML inspectors, and figures are reproducible and also stay out of git.
- This repository lives under OneDrive and syncs to the cloud; close any open Excel/PowerPoint files before moving
  or regenerating them (lock files make a move fail). Large, rebuildable artefacts should be kept out of the synced
  tree where practical.
