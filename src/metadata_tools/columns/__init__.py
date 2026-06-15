################################################################################
# columns/__init__.py: Assemble the geometry column definitions
#
# Replaces the former exec()-based loader in columns.py. Each COLUMNS_* file is
# now a real, importable submodule (body/ring/sky/sun), and the names they
# define are re-exported here so callers can keep using
# `import metadata_tools.columns as col`.
################################################################################
from metadata_tools.bodies import BODIES
from metadata_tools.columns.body import (
    BODY_COLUMNS,
    BODY_DETAILED_COLUMNS,
    BODY_DETAILED_DICT,
    BODY_GRIDLESS_COLUMNS,
    BODY_SUMMARY_COLUMNS,
    BODY_SUMMARY_DICT,
    BODY_TILE_DICT,
    BODY_TILES,
)
from metadata_tools.columns.ring import (
    ANSA_COLUMNS,
    OUTER_RING_TILE_DICT,
    OUTER_RING_TILES,
    RING_AZ,
    RING_COLUMNS,
    RING_DETAILED_COLUMNS,
    RING_DETAILED_DICT,
    RING_GRIDLESS_COLUMNS,
    RING_SUMMARY_COLUMNS,
    RING_SUMMARY_DICT,
    RING_TILE_DICT,
    RING_TILES,
)
from metadata_tools.columns.sky import (
    SKY_COLUMNS,
    SKY_TILES,
)
from metadata_tools.columns.sun import (
    SUN_COLUMNS,
    SUN_DETAILED_COLUMNS,
    SUN_GRIDLESS_COLUMNS,
    SUN_SUMMARY_COLUMNS,
)

__all__ = [
    'ANSA_COLUMNS',
    'BODIES',
    'BODY_COLUMNS',
    'BODY_DETAILED_COLUMNS',
    'BODY_DETAILED_DICT',
    'BODY_GRIDLESS_COLUMNS',
    'BODY_SUMMARY_COLUMNS',
    'BODY_SUMMARY_DICT',
    'BODY_TILES',
    'BODY_TILE_DICT',
    'OUTER_RING_TILES',
    'OUTER_RING_TILE_DICT',
    'RING_AZ',
    'RING_COLUMNS',
    'RING_DETAILED_COLUMNS',
    'RING_DETAILED_DICT',
    'RING_GRIDLESS_COLUMNS',
    'RING_SUMMARY_COLUMNS',
    'RING_SUMMARY_DICT',
    'RING_TILES',
    'RING_TILE_DICT',
    'SKY_COLUMNS',
    'SKY_TILES',
    'SUN_COLUMNS',
    'SUN_DETAILED_COLUMNS',
    'SUN_GRIDLESS_COLUMNS',
    'SUN_SUMMARY_COLUMNS',
]
