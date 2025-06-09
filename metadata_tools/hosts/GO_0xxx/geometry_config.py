################################################################################
# host_config.py for GLL SSI
#
#  Host-specific definitions and utilites for geometry file generation.
#
################################################################################
import oops
import oops.hosts.galileo.ssi as ssi
import metadata_tools.util as util
import metadata_tools.hosts.GO_0xxx.host_init


################################################################################
# SCLK-dependent mission-specific data (required)
################################################################################
# SYSTEM and SECONDARIES are always included in the body table regardless
# of whether the intersect the FOV.
#      SCLK_START range (inclusive)   PRIMARY   SECONDARIES
DEFAULT_BODIES_TABLE = [
    (('00180626.00', '00190641.00'), 'VENUS',   []),
    (('00597197.00', '00623035.00'), 'EARTH',   []),
    (('01645330.00', '01663247.00'), 'EARTH',   []),
    (('01973272.00', '06475387.00'), 'JUPITER', [])]


BORDER = 25                  # in units of full-size SSI pixels
NAC_PIXEL = 6.0e-6           # approximate full-size SSI pixel in units of radians
EXPAND = BORDER * NAC_PIXEL  # Amount to expand FOV in units of radians
from_index = ssi.from_index

################################################################################
# Meshgrid functions (required)
################################################################################

#===============================================================================
def meshgrids(sampling):

    MODE_SIZES  = {"FULL": 1,
                   "HMA":  1,
                   "HIM":  1,
                   "IM8":  1,
                   "HCA":  1,
                   "IM4":  1,
                   "XCM":  1,
                   "HCM":  1,
                   "HCJ":  1,
                   "HIS":  2,
                   "AI8":  2}

    meshgrids = {}
    for mode in MODE_SIZES.keys():
        pixel_wrt_full = MODE_SIZES[mode]
        pixels = 800 / MODE_SIZES[mode]

        # Define sampling of FOV
        origin = -float(BORDER) / pixel_wrt_full
        limit = pixels - origin

        # Revise the sampling to be exact
        samples = int((limit - origin) / sampling + 0.999)
        under = (limit - origin) / samples

        # Construct the meshgrid
        limit += 0.0001
        meshgrid = oops.Meshgrid.for_fov(ssi.SSI.fovs[mode], origin,
                                         undersample=under, limit=limit, swap=True)
        meshgrids[mode] = meshgrid

    return meshgrids

#===============================================================================
def meshgrid(meshgrids, snapshot):
    """Determines the meshgrid given the dictionary derived from the SSI index file.

    Args:
        snapshot (oops.Observation): Observation object a GOSSI image.
        meshgrids (oops.Meshgrid): Meshgrid objects to choose from.

    Returns:
        None.
    """
    return meshgrids[snapshot.dict['TELEMETRY_FORMAT_ID']]


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


################################################################################
# SSI geometry functions (required)
################################################################################

#===============================================================================
def target_name(dict):
    """Determines the target name from the snapshot's dictionary. If the given
    name is "SKY", it checks the CIMS ID and the TARGET_DESC for something
    different.

    Args:
        dict (dict): Snapshot observation dictionary.

    Returns:
        str: Target name.
    """

    return dict["TARGET_NAME"]

    target = dict["TARGET_NAME"]
    if target != "SKY":
        return target

    id = dict["OBSERVATION_ID"]
    abbrev = id[id.index("_"):][4:6]

    if abbrev == "SK":
        desc = dict["TARGET_DESC"]
        if desc in defs.BODY_NAMES:
            return desc

    try:
        return col.CIMS_TARGET_ABBREVIATIONS[abbrev]
    except KeyError:
        return target

#===============================================================================
def cleanup():
    """Cleanup function for geometry code.  This function is called after
       the geometry table and labels are written, before exiting.

        Args: None
        Returns: None.
    """
    pass
