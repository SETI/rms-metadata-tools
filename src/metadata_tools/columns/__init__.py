"""Assemble and re-export the geometry column definitions.

This package gathers the body, ring, sky, and sun geometry column definitions
from its submodules (``body``, ``ring``, ``sky``, ``sun``) and re-exports them,
along with the body list, under a single namespace. Callers import it as
``import metadata_tools.columns as col`` and reference the assembled column
lists, replacement dictionaries, and tile definitions used to build the
geometry tables.
"""
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
