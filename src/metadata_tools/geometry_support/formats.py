################################################################################
# geometry_support/formats.py - Host mission-table access.
################################################################################
"""The active host's mission table, with spacecraft-clock strings resolved.

Everything else about a geometry column -- its existence, formats, nulls,
ranges, and computation -- comes from the host's label templates, read back by
:mod:`metadata_tools.geometry_support.label_schema`.
"""
from typing import Any

import metadata_tools.util as util
from metadata_tools.config import current_host_id, get_geometry_config, get_spacecraft_id

_mission_table_cache: dict[str, list[Any]] = {}

#===============================================================================
def get_mission_table() -> list[Any]:
    """The active host's mission table, with each row's bounds converted to numbers.

    Computed once per host and cached, since the conversion of clock counts
    requires SPICE (via ``util.convert_mission_table``) and the source table
    does not change within a process.

    Returns:
        The host mission table, each row's span a ``util.MissionRange`` in clock
        ticks or TDB seconds.
    """
    host_id = current_host_id()
    if host_id not in _mission_table_cache:
        _mission_table_cache[host_id] = util.convert_mission_table(
            get_geometry_config().MISSION_TABLE, get_spacecraft_id())
    return _mission_table_cache[host_id]
