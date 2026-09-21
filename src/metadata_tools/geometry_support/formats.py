################################################################################
# geometry_support/formats.py - Host mission-table access.
################################################################################
"""The active host's mission table, with spacecraft-clock strings resolved.

Column format metadata used to live here. It now lives in two places, each the
natural home for its half: everything a PDS3 label can express -- the column
set and order, widths, print formats, nulls, and valid ranges -- comes from the
host's label templates via
:mod:`metadata_tools.geometry_support.label_schema`, and the rest -- unit
conversion, overflow formats, and null links -- lives beside the column
catalogs in :mod:`metadata_tools.columns.formats`.
"""
from typing import Any

import metadata_tools.util as util
from metadata_tools.config import current_host_id, get_geometry_config

_mission_table_cache: dict[str, list[Any]] = {}

#===============================================================================
def get_mission_table() -> list[Any]:
    """The active host's mission table, with SCLK strings converted to ticks.

    Computed once per host and cached, since the conversion requires SPICE
    (via ``util.convert_mission_table``) and the source table does not change
    within a process.

    Returns:
        The host mission table with spacecraft-clock strings converted to ticks.
    """
    host_id = current_host_id()
    if host_id not in _mission_table_cache:
        config = get_geometry_config()
        _mission_table_cache[host_id] = util.convert_mission_table(
            config.MISSION_TABLE, config.SC)
    return _mission_table_cache[host_id]
