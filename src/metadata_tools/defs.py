##########################################################################################
# defs.py: Definitions
##########################################################################################
"""Shared constants for the metadata tools.

Defines package paths, null markers, body-name lists, and ring-system radii used
throughout the index and geometry table generators.
"""
import sys

from filecache import FCPath

#####################
# Define constants
#####################
_metadata = sys.modules[__name__]

PARENT_DIR = FCPath(_metadata.__file__).parent
"""Directory containing the installed package."""

GLOBAL_TEMPLATE_PATH = PARENT_DIR / 'templates'
"""Directory holding the package's shared PDS3 label-template fragments."""

NULL = "null"
"""Null marker used in column definitions to denote an absent value."""

BODYX = "bodyx"
"""Placeholder body name, substituted per body by the column-definition
replacement helpers (see :func:`metadata_tools.util.replacement_dict`)."""

NAME_LENGTH = 12
"""Character width of a column that holds a body name."""

TRANSLATIONS: dict[str, str] = {}
"""Optional mapping of raw target names to canonical body names."""

BODY_NAMES = [
    'MERCURY',
    'VENUS',
    'EARTH',
    'MARS',
    'JUPITER',
    'SATURN',
    'URANUS',
    'NEPTUNE',
    'PLUTO'
]
"""Planet names whose systems are processed, in registry order."""

RING_SYSTEM_RADII = {
    'MERCURY':  0,
    'VENUS':    0,
    'EARTH':    0,
    'MARS':     0,
    'JUPITER':  128940.,
    'SATURN':   136780.,
    'URANUS':   51604.,
    'NEPTUNE':  62940.,
    'PLUTO':    0
    }
"""Outer radius (km) of each planet's main ring system; 0 if it has none."""
