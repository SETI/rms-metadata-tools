"""Assemble and re-export the geometry column definitions.

This package gathers the body, ring, sky, and sun geometry column definitions
from its submodules (``body``, ``ring``, ``sky``, ``sun``) and re-exports them,
along with the bodies registry accessor, under a single namespace. Callers import it as
``import metadata_tools.columns as col`` and reference the assembled column
lists and replacement dictionaries used to build the geometry tables.
"""
from metadata_tools.bodies import get_bodies_registry
from metadata_tools.columns.body import (
    BODY_COLUMNS,
    BODY_GRIDLESS_COLUMNS,
    BODY_SUMMARY_COLUMNS,
    get_body_summary_dict,
)
from metadata_tools.columns.ring import (
    ANSA_COLUMNS,
    RING_COLUMNS,
    RING_GRIDLESS_COLUMNS,
    RING_SUMMARY_COLUMNS,
    RING_SUMMARY_DICT,
)
from metadata_tools.columns.sky import (
    SKY_COLUMNS,
)
from metadata_tools.columns.sun import (
    SUN_COLUMNS,
    SUN_GRIDLESS_COLUMNS,
    SUN_SUMMARY_COLUMNS,
)

__all__ = [
    'ANSA_COLUMNS',
    'BODY_COLUMNS',
    'BODY_GRIDLESS_COLUMNS',
    'BODY_SUMMARY_COLUMNS',
    'RING_COLUMNS',
    'RING_GRIDLESS_COLUMNS',
    'RING_SUMMARY_COLUMNS',
    'RING_SUMMARY_DICT',
    'SKY_COLUMNS',
    'SUN_COLUMNS',
    'SUN_GRIDLESS_COLUMNS',
    'SUN_SUMMARY_COLUMNS',
    'get_bodies_registry',
    'get_body_summary_dict',
]
