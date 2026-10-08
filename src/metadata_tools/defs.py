##########################################################################################
# defs.py: Definitions
##########################################################################################
"""Shared constants for the metadata tools.

Defines package paths, null markers, and body-name lists used throughout the
index and geometry table generators.
"""
import sys

from filecache import FCPath

#####################
# Define constants
#####################
_metadata = sys.modules[__name__]

PARENT_DIR = FCPath(_metadata.__file__).parent
"""The installed metadata_tools package directory."""

GLOBAL_TEMPLATE_PATH = PARENT_DIR / 'templates'
"""Directory holding the package's shared PDS3 label-template fragments."""

NULL = "null"
"""Null marker used in column definitions to denote an absent value."""

BODYX = "bodyx"
"""Placeholder body name, substituted per body by the column-definition
replacement helpers (see :func:`metadata_tools.util.replace`)."""

NAME_LENGTH = 12
"""Character width of a column that holds a body name."""

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
