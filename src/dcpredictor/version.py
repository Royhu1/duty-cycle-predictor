"""Version metadata for the ``dcpredictor`` package.

The canonical version is the ``version`` field in ``pyproject.toml``. At runtime
it is read via ``importlib.metadata`` (populated by ``pip install``), falling back
to ``_FALLBACK_VERSION`` when running from an uninstalled source tree.

On release, bump BOTH the ``version`` in ``pyproject.toml`` and ``_FALLBACK_VERSION``
below, update ``VERSION_DATE`` / ``VERSION_DESCRIPTION`` and ``CHANGELOG.md``, then
tag ``vX.Y.Z`` (see ``.claude/rules/git-workflow.md``).
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

# Fallback used only when the package is not pip-installed (e.g. a raw source tree).
_FALLBACK_VERSION = "0.1.3"

try:
    __version__ = _dist_version("duty-cycle-prediction")
except PackageNotFoundError:  # pragma: no cover - source-tree fallback
    __version__ = _FALLBACK_VERSION

# Numeric tuple, ignoring any non-numeric suffix (e.g. dev/local build segments).
__version_info__ = tuple(int(part) for part in __version__.split(".") if part.isdigit())

# Human-facing release metadata (kept in sync manually on release).
VERSION_DATE = "2026-02-05"
VERSION_DESCRIPTION = "Add route-validity check to avoid infinite loops on very short routes"
