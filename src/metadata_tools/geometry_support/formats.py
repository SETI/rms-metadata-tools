################################################################################
# geometry_support/formats.py - Host mission-table access.
################################################################################
"""The active host's mission table, with spacecraft-clock strings resolved.

Column format metadata used to live here. All of it -- the column set and
order, widths, print formats, overflow formats, nulls, valid ranges, unit
conversions, backplane keys, masks, and null links -- now comes from the host's
label templates, read back by
:mod:`metadata_tools.geometry_support.label_schema`.
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
