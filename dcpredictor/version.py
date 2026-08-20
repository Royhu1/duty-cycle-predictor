"""Version metadata for the ``dcpredictor`` package.

The repository is not packaged or distributed, so this file is the **single
source of truth** for the package version. On release, bump ``__version__``,
update ``VERSION_DATE`` / ``VERSION_DESCRIPTION`` and ``CHANGELOG.md``, then
tag ``vX.Y.Z`` (see ``.claude/rules/git-workflow.md``).
"""

__version__ = "0.1.3"

# Numeric tuple, ignoring any non-numeric suffix (e.g. dev/local build segments).
__version_info__ = tuple(int(part) for part in __version__.split(".") if part.isdigit())

# Human-facing release metadata (kept in sync manually on release).
VERSION_DATE = "2026-02-05"
VERSION_DESCRIPTION = "Add route-validity check to avoid infinite loops on very short routes"
