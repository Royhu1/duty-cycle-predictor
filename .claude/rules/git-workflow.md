> Git workflow conventions — referenced from the root `CLAUDE.md` "## Git Workflow" section via `@import`.
> Editing here = editing the git / version / changelog conventions for the whole project (committed with `.claude/`).

### Version number (refers only to the `dcpredictor` package)

The version belongs only to the installable `dcpredictor` package (`dcpredictor/` at the repo root) and follows
SemVer. It is maintained in **`pyproject.toml` → `[project].version`** (the single source of truth);
`dcpredictor/version.py` reads it at runtime via `importlib.metadata` and carries a `_FALLBACK_VERSION` for
uninstalled source trees. The demo notebooks (`demo/`) are **not** part of this scheme and are not tagged.

- `patch` (x.x.**N**): bug fixes / minor adjustments, no interface change
- `minor` (x.**N**.0): new features, backward compatible
- `major` (**N**.0.0): breaking interface changes

### Standard version-release procedure

1. Complete the code change →
2. Update `dcpredictor/README.md` (if architecture / public API / fields changed) →
3. Bump `version` in `pyproject.toml` **and** `_FALLBACK_VERSION` + metadata in `dcpredictor/version.py` →
4. Add an entry to `dcpredictor/CHANGELOG.md` →
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

`tests/data/` contents (except its README) / generated CSV·HTML / experiment outputs / large binaries (PDF/PPTX)
are not committed (see `.gitignore`). The repo tracks only source code + documentation.

### Changelogs

- The package keeps a SemVer changelog at `dcpredictor/CHANGELOG.md` (one section per released version) — the
  single changelog of this repository. There is no weekly project changelog here; project-level work is recorded
  in the repositories that consume `dcpredictor`.
