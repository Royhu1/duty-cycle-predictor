# Project Overview

**duty-cycle-predictor** predicts vehicle duty cycles (speed, gradient, and energy/fuel profiles) from a route,
using external routing/elevation APIs and a longitudinal vehicle-dynamics model. The core is the `dcpredictor`
package at the repository root (imported directly — the repository is not packaged or distributed). This
repository is scoped to the development and testing of the predictor itself; paper and project-level analysis
work lives in separate repositories.

**Core workflow:** origin/destination → HERE route → SRF elevation → speed profile → gradient profile → energy/fuel.

## Project Structure

> The project has a **hierarchical structure** (root + sub-projects / workspaces). At every level, that level's
> `README.md` is the **single source of truth** (structure + conventions + how to run it). The imported root
> README below is the overall project map; the package's own architecture reference is `dcpredictor/README.md`.

@./README.md

## Python Environment

This project uses a dedicated conda environment named **`dcp`** (Python 3.10).

- **Non-interactive shell (Claude Code):** prefix commands, e.g. `conda run -n dcp python ...`, `conda run -n dcp pytest`.
- **Interactive terminal:** `conda activate dcp` then run normally.
- No installation step: the package sits at the repo root and is imported directly. Run commands from the
  repository root; the demo notebooks add the root to `sys.path` in their first cell.

## Code Style

@./.claude/rules/code-style.md

## Naming Convention

@./.claude/rules/naming.md

## Git Workflow

@./.claude/rules/git-workflow.md

## Housekeeping

@./.claude/rules/housekeeping.md

## Language Convention

- All text committed to the repository — code, comments, docstrings, documentation, changelogs, configs — is
  written in **English**. Chinese is used only for interactive chat and any gitignored local notes.

## Notes

- **Local override (highest priority):** if `CLAUDE.local.md` (gitignored) conflicts with `CLAUDE.md`,
  `CLAUDE.local.md` takes precedence.
