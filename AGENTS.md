# Agent instructions

## Project-specific rules (authoritative)

The files under `.claude/rules/` (naming.md, code-style.md, git-workflow.md,
housekeeping.md, ...) are this project's own conventions. **They take precedence
over the global rules below** — read them first.

<!-- BEGIN GLOBAL RULES (generated) -->
<!-- GENERATED FILE - DO NOT EDIT.
     Source of truth: ~/.claude/rules/{repo-roles,naming,code-style,git-workflow,housekeeping}.md @ bc12e98 (2026-08-20)
     To change these rules: edit the source files, then run /sync-agent-rules in Claude Code
     (or: powershell -File ~/.claude/rules/tools/build-agents-md.ps1). -->
# Repository Roles (Global) ／仓库角色与职责划分

> Personal defaults for ALL projects. Project rules override.
> Pick one role per repository and state it in the first line of its README. ／每个仓库只承担一种角色，README 首行写明。

## 0. Three roles ／三种角色

- **standalone** — a self-contained tool, app or one-off project. No pairing, no unified route. **Most
  repositories are this** ／多数仓库属于此类: utilities, web/video apps, 业余 projects.
- **core repo** + **workspace** — the *pair* below, used only when research code must separate a reusable
  algorithm from the experiments that consume it. Do not impose it on a project that is not that.

## 1. The pair ／一对仓库

| | `<name>` — **core repo** ／主开发仓库 | `<name>-workspace` — **workspace** ／实验工作区 |
|---|---|---|
| Holds | one algorithm / library + its unit tests + small demos | experiments, large-scale studies, figures for talks and papers |
| Audience | shareable, often public | private, my own research work |
| Medium | modules with docstrings and tests | notebooks |
| Tracked in git | source + documentation only | experiment code + documentation only |
| Versioned | SemVer in ONE place, tagged `vX.Y.Z` | none — git log + `changelogs/` are the record |
| Commit types | `feat:` `fix:` `refactor:` `docs:` `test:` | mostly `exp:` |
| Skeleton | `<pkg>/ demo/ tests/ tmp/` | `paths.py <experiment>/ data/ changelogs/ archive/ tmp/` |

- **Not packaged by default** ／默认不打包: personal research code is *imported*, not `pip install`-ed. Keep the
  package directory at the repository root (flat layout), version it in `<pkg>/version.py`, and add
  `[build-system]`/`[project]` tables only when someone outside actually needs `pip install`. `pyproject.toml`
  otherwise holds tool config only.
- Papers and conferences are **neither** — they live in their own folder (`MEETING-CONFERENCE/<conf>-YYYY-MM`).

## 2. Division of responsibility ／职责划分

- An algorithm change belongs in the **core repo**, on a feature branch, with a test. **Never copy core code into
  a workspace** ／绝不把核心代码复制进工作区.
- **Rule of three**: logic used by 3+ experiments and already stable → promote it into the core package (SemVer
  minor bump), do not keep copying it.
- Model parameters and presets that describe the *system* live in the core repo and are read through its public
  loaders — never by file path. Experiment-specific configuration stays in the workspace.
- The core repo's own data zone holds only small fixtures for its tests and demos; bulk measured data belongs to
  the workspace.

## 3. The unified route ／统一路由 (workspace)

- **Exactly one module — `paths.py` at the workspace root — knows where everything is.** A hard-coded absolute
  path anywhere else is a defect. Moving the core repo must be a one-line change. ／别处出现绝对路径即为缺陷。
- It resolves the core repo from the env var `<NAME>_ROOT`, else the sibling `../<name>`; `bootstrap()` prepends
  it to `sys.path` and loads the API keys (`.env` in the workspace → core repo → a shared key folder).
- Per-experiment zones come from a helper (`experiment_paths(<experiment>, <key>)` → `data` / `results` /
  `figures` / `summary`), all gitignored and created on demand.
- Each experiment directory is a **self-contained reproducible archive**: standard library + pip packages + the
  core package + its own files; it never reads another experiment's outputs.
- The only path boilerplate allowed anywhere, at any depth:

  ```python
  import sys
  from pathlib import Path

  _cwd = Path.cwd()
  WORKSPACE_ROOT = next(p for p in [_cwd, *_cwd.parents] if (p / "paths.py").exists())
  sys.path.insert(0, str(WORKSPACE_ROOT))

  from paths import bootstrap, experiment_paths      # noqa: E402
  bootstrap()
  ```

# Naming Conventions (Global) ／全局命名规范

> Personal defaults for ALL projects. Project-level rules override this file.
> Apply to NEW artefacts only — never mass-rename existing files (grandfathering).
> Outside a code repository, only §1, §5, §6 apply.
> ／项目级规则优先；只约束新建物，存量不追溯改名；非仓库目录仅 §1/§5/§6 生效。

## 1. Project & top-level folders ／项目与顶层文件夹

- New project folders: **kebab-case** — `duty-cycle-predictor`, `srf-api-ai-agent`.
- Meeting/conference folders: `<会议名>-YYYY-MM` (zero-padded month) — `ITSC-2026-09`.
- Chinese folder names ONLY for admin/inbox buckets outside repos (`例会`, `未归档`) — never for code repos.
- Git worktree variants: `<repo>.wt-<desc>` suffix.

## 2. Repository skeleton ／仓库骨架

- In-repo subfolders: lowercase **snake_case** — `extended_eval`, `trip_level_metrics`.
- Standard zones: `src/ data/ doc/ tests/ tmp/ archive/ changelogs/` (cleanup policy → housekeeping.md).
- Grandfathering: existing non-conforming paths stay; renames are deliberate, separate commits.

## 3. Files by type ／按类型的文件命名

- Scripts: verb-prefix `generate_* / analyse_* / calibrate_* / extract_* / build_*` — **British spelling** (`analyse`, not `analyze`).
- One-off scripts: `_tmp_*.py`, live in `tmp/`, gitignored, deleted after use.
- Notebooks: snake_case, prefixed by model/task — `calibrate_engine_efficiency.ipynb`.
- Data files: compact `YYYYMMDD` in file/dir names; period = `YYYYMMDD_YYYYMMDD`.
- Figures: `<model>_<what>.png`, reproducible from a committed script (no plot-and-delete); slide assets `fig_<content>.png`.
- Deliverables (slides/poster/speech): `YYYYMMDD_<type>_[<desc>_]vX.Y.ext` — `20260812_slides_v1.1.pptx`; type ∈ slides/poster/speech/program/agenda/CFP/notes.
- Docs: `README.md` is the authoritative English version; `*.zh.md` is the gitignored Chinese reading copy.
- Skills / agents / commands: **kebab-case** — `sync-agent-rules`.

## 4. Identifiers in code ／代码内标识符

→ see `code-style.md` (PEP 8 table, unit suffixes, abbreviation register policy, TS rules).

## 5. Language rules ／中英文使用

- Everything committed is **English**: code, comments, docstrings, README, commit messages, changelogs.
- Chinese ONLY for: interactive chat, gitignored notes (`*.zh.md`, local working docs), admin folders outside repos.
- British English spelling throughout.

## 6. Dates & versions ／日期与版本

- ISO 8601 everywhere: `YYYY-MM-DD` in prose/data fields; compact `YYYYMMDD` inside file/dir names (sorts chronologically).
- Code releases: SemVer tags `vX.Y.Z` (→ git-workflow.md). Deliverable files: `vX.Y`; `vFinal` allowed for the delivered copy.

# Code Style (Global) ／全局代码风格

> Personal defaults for ALL projects. Project rules override.
> Each project's own `code-style.md` holds its abbreviation register, environment names and version ceilings.

## Python — PEP 8

| Object | Style | Example |
|---|---|---|
| Package / module file | `snake_case` | `data_fetcher.py`, `models.py` |
| Function / method / variable | `snake_case` | `calculate_wheel_power` |
| Class | `PascalCase` | `ElevationCache` |
| Constant / module-level config | `UPPER_SNAKE_CASE` | `AIR_DENSITY`, `BASE_DIR` |
| Internal / private | leading underscore | `_safe_num()` |
| Test files | `test_<module>.py` | `test_models.py` |

- **Quantities carrying physical units state the unit in the name** — `mass_kg`, `velocity_mps`, `gradient_degrees`, `wheel_power_kW`, `fuel_rate_L_hr`. The unit keeps its own casing. Never drop the suffix. ／物理量标识符必须带单位后缀，单位保留原大小写。
- Identifiers always in English; abbreviations must be **registered before use** in the project's own `code-style.md` (e.g. `lvd` = longitudinal vehicle dynamics). No unregistered abbreviations. ／缩写先在项目规则里登记后再使用。
- Prefer `pathlib.Path`; f-strings for formatting.
- Secrets from `.env` via `python-dotenv` — never hard-code keys, never echo their values.
- Notebooks: reusable logic promoted into `src/` and imported (`%autoreload 2`); clear bulky cell outputs before committing.
- Legacy Chinese comments/docstrings: migrate to English opportunistically when a function is touched — do not mass-rewrite.

## TypeScript / React

- Components: `PascalCase.tsx`; entry/config lowercase (`index.ts`, `remotion.config.ts`).
- Functions / variables: `camelCase`; types / interfaces / components: `PascalCase`.

# Git Workflow (Global) ／全局 Git 约定

> Personal defaults for ALL projects. Project rules override (e.g. release-line specifics).

## Commit messages — Conventional Commits

- `feat:` / `fix:` / `refactor:` / `docs:` / `chore:` / `test:` / `exp:` (notebook experiment iteration).
- Meaningless messages ("update", "wip", "checkpoint") are forbidden. Written in English.

## Branches

- `main` is the stable mainline — do not develop directly on main.
- Feature branches: `feat/<description>` / `fix/<description>` / `exp/<description>`.

## Versioning

- Projects with a release line: **SemVer** tags `vX.Y.Z`; the version lives in ONE source of truth (e.g. `pyproject.toml`). Notebook-centric repos have no version numbers — git log + changelog is the record.

## Pushing requires user consent (mandatory) ／push 必须先征得同意

- **Every `git push` must first obtain explicit consent — never push autonomously.** Consent is per-push, not standing authorisation. Commit / branch / local merge may proceed as usual.

## Changelog

- Repos with a `changelogs/` zone: weekly file `changelog_YYYYMMDD_YYYYMMDD.md` (Mon–Sun), English, Q&A format; append to the current week's file.

## Not committed

- `.env`, caches, `data/`, `results/`, `tmp/`, `archive/`, `*.zh.md` — gitignored by default (seeded by the project template).

# Housekeeping (Global) ／全局整理约定

> Personal defaults for ALL projects. Project rules override (e.g. cache cost warnings).

## Zones ／分区

| Zone | Purpose | Cleanup |
|---|---|---|
| `tmp/` | one-off scratch: logs, intermediate CSVs, debug figures, `_tmp_*.py` | clean after use |
| `archive/` | recycle bin for superseded artefacts | **in only, never out**; root scratch → `archive/root_scratch_<YYYYMMDD>/` |
| `cache/` | expensive-to-rebuild API caches | do not clean lightly — check the project's rules for cost warnings |

- **Keep the repository root clean** — no stray scripts, logs or screenshots at root.
- **Prefer archiving over deletion** ／宁归档不删除: move into `archive/` to preserve traceability; only delete genuinely reproducible waste.

## OneDrive specifics ／OneDrive 注意事项

- Repos under OneDrive hold code, docs and small figures only. Large rebuildable artefacts go to a machine-local root `D:\<project>_local\` (not in git, not synced) — never scattered in `D:\tmp`.
- Open Office files (`~$*.pptx` lock files) break moves/renames — close them first.
- Avoid symlinks inside OneDrive-synced trees.
<!-- END GLOBAL RULES (generated) -->