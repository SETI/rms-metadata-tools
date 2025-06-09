################################################################################
# defs.py: Definitions
################################################################################
import sys
from pathlib import Path

###############################
# Define constants
###############################
_metadata = sys.modules[__name__]
COLUMN_DIR = Path(_metadata.__file__).parent / 'column'
GLOBAL_TEMPLATE_PATH = Path(_metadata.__file__).parent / 'templates'
NULL = "null"
BODYX = "bodyx"     # Placeholder for an arbitrary body to be filled in by
                    # replacement_dict()
NAME_LENGTH = 12

# Maintain a list of translations for target names
TRANSLATIONS = {}

################################################################################
# List of body names
################################################################################
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

################################################################################
# Ring definitions
################################################################################
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
