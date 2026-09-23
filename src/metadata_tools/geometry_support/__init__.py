################################################################################
# geometry_support package - Tools for generating geometry tables.
#
# Generates PDS3 geometry metadata tables (sky, ring, body, sun, inventory) and
# their labels from SPICE-derived backplanes. This module re-exports the public
# API: the label-schema resolver, the Record and Suite classes, the table
# classes, and the process entry points.
################################################################################
"""Geometry table generation engine: body, ring, sky, sun, and inventory tables."""
from metadata_tools.geometry_support.formats import get_mission_table
from metadata_tools.geometry_support.label_schema import (
    ColumnStub,
    ResolvedColumn,
    TableSchema,
    resolve_schema,
)
from metadata_tools.geometry_support.process import get_args, process_tables
from metadata_tools.geometry_support.record import Record
from metadata_tools.geometry_support.suite import Suite
from metadata_tools.geometry_support.tables import (
    BodyTable,
    InventoryTable,
    RingTable,
    SkyTable,
    SunTable,
)

__all__ = [
    'BodyTable',
    'ColumnStub',
    'InventoryTable',
    'Record',
    'ResolvedColumn',
    'RingTable',
    'SkyTable',
    'Suite',
    'SunTable',
    'TableSchema',
    'get_args',
    'get_mission_table',
    'process_tables',
    'resolve_schema',
]
