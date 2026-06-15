################################################################################
# geometry_support package - Tools for generating geometry tables.
#
# This package was split out of the former single-file geometry_support.py
# module (see plans/plan1_split_geometry_support.md). The public import surface
# is preserved: `import metadata_tools.geometry_support as geom` exposes the
# same names it always did.
################################################################################
from metadata_tools.geometry_support.formats import ALT_FORMAT_DICT, FORMAT_DICT, MISSION_TABLE
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
    'ALT_FORMAT_DICT',
    'FORMAT_DICT',
    'MISSION_TABLE',
    'BodyTable',
    'InventoryTable',
    'Record',
    'RingTable',
    'SkyTable',
    'Suite',
    'SunTable',
    'get_args',
    'process_tables',
]
