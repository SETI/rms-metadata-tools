"""General host-specific definitions and utilities for Galileo SSI (GLL SSI).

This module holds settings and helpers shared across the index, geometry, and
cumulative generators for the GO_0xxx collection.
"""
from pathlib import Path

from filecache import FCPath

import metadata_tools.util as util

template_name = 'GO_0xxx_supplemental_index'

################################################################################
# Spacecraft clock modulo
################################################################################
SCLK_BASES: list[int] = [16777215, 91, 10, 8]


################################################################################
# Utilities (required)
################################################################################

#===============================================================================
def get_volume_id(label_path: str | Path | FCPath) -> str:
    """Determine the volume ID for this collection from the label path.

    Used when there is no observation or loaded label available.

    Parameters:
        label_path: Path to the PDS label.

    Returns:
        The volume ID.
    """
    top = 'GO_0xxx'
    return util.splitpath(FCPath(label_path), top)[1].parts[0]

