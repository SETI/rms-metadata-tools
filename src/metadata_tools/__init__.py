##########################################################################################
# metadata-tools/__init__.py
##########################################################################################
"""PDS Ring-Moon Systems Node metadata table generator.

``rms-metadata-tools`` generates PDS3 index, geometry, and cumulative metadata
tables (and their PDS3 labels) for planetary science data collections.  Each
table row holds metadata for one data file (e.g. an image).

Three stages run in order for each collection:

1. **Index** — supplemental index columns sourced from PDS labels
   (``metadata-index HOST_ID ...``).
2. **Geometry** — geometric quantities computed from SPICE via ``oops``
   (``metadata-geometry HOST_ID ...``).
3. **Cumulative** — per-volume table concatenations across a volume tree
   (``metadata-cumulative HOST_ID ...``).

Per-collection configuration lives in
``src/metadata_tools/hosts/<HOST>/`` (e.g. ``GO_0xxx/`` for Galileo SSI).
"""
##########################################################################################
import os as _os

from filecache import FCPath as _FCPath

_env_file = _FCPath(__file__).parent.parent.parent / '.env'
try:
    with _env_file.open(encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                _k = _k.strip()
                # Expand $VAR references in the value against vars already set (including
                # those set by earlier lines in this .env file), then apply as a default.
                _v = _os.path.expandvars(_v.strip())
                _os.environ.setdefault(_k, _v)
except FileNotFoundError:
    pass

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    __version__ = 'Version unspecified'
