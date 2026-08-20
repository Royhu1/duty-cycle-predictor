> Git workflow conventions — referenced from the root `CLAUDE.md` "## Git Workflow" section via `@import`.
> Editing here = editing the git / version / changelog conventions for the whole project (committed with `.claude/`).

### Version number (refers only to the `dcpredictor` package)

The version belongs only to the installable `dcpredictor` package (`src/dcpredictor/`) and follows SemVer. It is
maintained in **`pyproject.toml` → `[project].version`** (the single source of truth); `src/dcpredictor/version.py`
reads it at runtime via `importlib.metadata` and carries a `_FALLBACK_VERSION` for uninstalled source trees. The
exploratory workspaces (`notebooks/`, `examples/`) are **not** part of this scheme and are not tagged.

- `patch` (x.x.**N**): bug fixes / minor adjustments, no interface change
- `minor` (x.**N**.0): new features, backward compatible
- `major` (**N**.0.0): breaking interface changes

### Standard version-release procedure

1. Complete the code change →
2. Update `src/dcpredictor/README.md` (if architecture / public API / fields changed) →
3. Bump `version` in `pyproject.toml` **and** `_FALLBACK_VERSION` + metadata in `src/dcpredictor/version.py` →
4. Add an entry to `src/dcpredictor/CHANGELOG.md` →
5. `git commit` → 6. `git tag vX.Y.Z`.

### Commit messages (Conventional Commits)

`feat:` new feature / `fix:` fix / `refactor:` refactor / `docs:` documentation / `chore:` deps & maintenance /
`test:` tests. Meaningless messages (e.g. "update", "checkpoint", "wip") are discouraged for substantive changes.

### Branch strategy

- Do not develop directly on the mainline (`master`/`main`). New work goes on feature branches:
  `feat/<description>` / `fix/<description>` / `refactor/<description>`.
- Merge locally: `git checkout <mainline> && git merge <branch>`; if a version change is involved, tag after merging.

### Pushing requires explicit user consent (mandatory)

- **Every `git push` must first obtain the user's explicit consent** — state what will be pushed and the target
  (branch, remote, whether tags are included). Consent for one push is not standing authorisation for later pushes.
- Local commit / branch / merge may proceed per the workflow; only the push step needs sign-off.

### Artefacts not committed to git

`data/` / `results/` / `ref/` / generated CSV·HTML / experiment outputs / large binaries (PDF/PPTX) /
`archive/` contents are not committed (see `.gitignore`). The repo tracks only source code + documentation.

### Changelogs

- The package keeps a SemVer changelog at `src/dcpredictor/CHANGELOG.md` (one section per released version).
- Project-level work is summarised in weekly files `changelogs/changelog_YYYYMMDD_YYYYMMDD.md` (Mon–Sun) in Q&A
  form (task prompt → result → verification); append to the current week's file or create it. New entries are
  written in English.
