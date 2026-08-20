> Tidiness and local-storage conventions — referenced from the root `CLAUDE.md` "## Housekeeping" section via `@import`.
> Editing here = editing the temp-file cleanup / archiving conventions for the whole project (committed with `.claude/`).

> This file governs **project tidiness and where files land**. For Python identifiers / one-off script naming see
> `code-style.md`; for data / directory naming see `naming.md`; for branch / commit / changelog see `git-workflow.md`.

### Temporary files: zones and cleanup

| Zone | Purpose | In git | Cleanup policy |
|------|---------|--------|----------------|
| `tmp/` (create on demand) | one-off scratch: logs, intermediate CSVs, debug figures, `_tmp_*.py` | No | clean after use |
| `archive/` | recycle bin: superseded / retired files (e.g. orphaned scripts, old slide decks, deprecated notebooks) | No (only `.gitkeep` tracked) | in only, never out |

- **Keep the repository root clean**: do not drop one-off scripts, logs, or env dumps directly in the root. They
  belong in a workspace's own `scripts/`, in `tmp/`, or are moved into `archive/`.
- **Prefer archiving over deletion**: clean up by *moving* a file into `archive/`, preserving traceability; only
  delete genuinely reproducible waste. On Windows, `Move-Item` is safer than `Remove-Item` (the sandbox may
  intercept deletes on top-level paths).

### Data and large files

- Raw GPS data lives under `data/<REG>/` and is **never committed** (gitignored). Generated results, HTML
  inspectors, and figures are reproducible and also stay out of git.
- This repository lives under OneDrive and syncs to the cloud; close any open Excel/PowerPoint files before moving
  or regenerating them (lock files make a move fail). Large, rebuildable artefacts should be kept out of the synced
  tree where practical.
