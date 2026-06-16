################################################################################
# host_config.py for GLL SSI
#
#  General host-specific definitions and utilites.
#
################################################################################
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
    """Utility function to determine the volume ID for this collection
       using the label path when there is no observation or label available.

    Args:
        label_path: Path to the PDS label.

    Returns:
        The volume ID.
    """
    top = 'GO_0xxx'
    return util.splitpath(FCPath(label_path), top)[1].parts[0]

