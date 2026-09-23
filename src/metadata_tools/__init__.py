##########################################################################################
# metadata-tools/__init__.py
##########################################################################################
"""PDS Ring-Moon Systems Node metadata table generator.

``rms-metadata-tools`` generates PDS3 index, geometry, and cumulative metadata
tables (and their PDS3 labels) for planetary science data collections. Each
table row holds metadata for one data file (e.g. an image).

Three stages run in order for each collection:

1. **Index** - supplemental index columns sourced from PDS labels
   (``metadata-index HOST_ID ...``).
2. **Geometry** - geometric quantities computed from SPICE via ``oops``
   (``metadata-geometry HOST_ID ...``).
3. **Cumulative** - per-volume table concatenations across a volume tree
   (``metadata-cumulative HOST_ID ...``).

Per-collection configuration lives in
``src/metadata_tools/hosts/<HOST>/`` (e.g. ``GO_0xxx/`` for Galileo SSI).
"""
##########################################################################################
import os as _os
from pathlib import Path as _Path

from filecache import FCPath as _FCPath

ENV_FILE_VAR = 'RMS_METADATA_ENV'


def _find_dotenv(cwd: _Path | None = None,
                 package_file: str | _Path = __file__) -> _FCPath | None:
    """Locate the ``.env`` file supplying environment defaults.

    The first match wins:

    1. The path named by ``$RMS_METADATA_ENV``, if that variable is set.
    2. A ``.env`` in the current directory or the nearest parent that has one.
    3. A ``.env`` at the source-checkout root (the directory holding
       ``pyproject.toml`` above ``src/metadata_tools/``); an installed package has
       no such root, so this step applies only to a source checkout.

    Parameters:
        cwd: Directory from which the upward search starts; the current working
            directory if None.
        package_file: Path of this package's ``__init__.py``, from which the
            source-checkout root is derived.

    Returns:
        The ``.env`` path, or None if no step finds one.

    Raises:
        FileNotFoundError: If ``$RMS_METADATA_ENV`` names a file that does not exist.
    """
    explicit = _os.environ.get(ENV_FILE_VAR)
    if explicit:
        path = _Path(_os.path.expanduser(explicit))
        if not path.is_file():
            raise FileNotFoundError(f'${ENV_FILE_VAR} names a missing file: {explicit}')
        return _FCPath(path)

    start = cwd if cwd is not None else _Path.cwd()
    for directory in (start, *start.parents):
        if (directory / '.env').is_file():
            return _FCPath(directory / '.env')

    root = _Path(package_file).resolve().parents[2]
    if (root / 'pyproject.toml').is_file() and (root / '.env').is_file():
        return _FCPath(root / '.env')
    return None


def _load_dotenv(path: _FCPath) -> None:
    """Apply a ``.env`` file's ``NAME=value`` lines as environment defaults.

    Blank lines and ``#`` comments are ignored. Each value has ``$VAR``
    references expanded against the variables already set, including those set
    by earlier lines of the same file, and is applied only if the variable is not
    already set, so the shell environment takes precedence.

    Parameters:
        path: The ``.env`` file to read.
    """
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                _os.environ.setdefault(key.strip(), _os.path.expandvars(value.strip()))


_env_file = _find_dotenv()
if _env_file is not None:
    _load_dotenv(_env_file)

__all__ = ['__version__']

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    __version__ = 'Version unspecified'
