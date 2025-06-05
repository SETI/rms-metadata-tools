################################################################################
# host_config.py for GLL SSI
#
#  General host-specific definitions and utilites.
#
################################################################################
import metadata_tools.util as util


################################################################################
# Spacecraft clock modulo
################################################################################
SCLK_BASES = [16777215, 91, 10, 8]


################################################################################
# Utilities (required)
################################################################################

#===============================================================================
def get_volume_id(label_path):
    """Utility function to determine the volume ID for this collection
       using the label path when there is no observation or label available.

    Args:
        label_path (str): Path to the PDS label.

    Returns:
        None.
    """
    top = 'GO_0xxx'
    return util.splitpath(label_path, top)[1].parts[0]


