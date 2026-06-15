################################################################################
# geometry_support/masks.py - Excluded-pixel mask construction.
#
# Config-free: depends only on oops and numpy so it can be unit-tested without
# the host geometry_config plugin.
################################################################################
import numpy as np
import oops


#===============================================================================
def construct_excluded_mask(backplane, target, primary, mask_desc, *,
                            blocker=None, ignore_shadows=True):
    """Return a mask using the specified target, maskers and shadowers to
    indicate excluded pixels.

    Args:
        backplane (oops.Backplne): The backplane defining the target surface.
        target (str): The name of the target surface.
        primary (str): Name of primary, e.g., "SATURN".
        mask_desc (masker, shadower, face), where:
            Masker      a string identifying what surfaces can obscure the
            target. It is a concatenation of:
            "P" to let the planet obscure the target;
            "R" to let the rings obscure the target;
            "M" to let the blocker body obscure the target.
            shadower    a string identifying what surfaces can shadow the
            target. It is a string containing:
            "P" to let the planet shadow the target;
            "R" to let the rings shadow the target;
            "M" to let the blocker body shadow the target.
            face        a string identifying which face(s) of the surface to
            include:
            "D" to include only the day side of the target;
            "N" to include only the night side of the target;
            ""  to include both faces of the target.
        blocker (str, optional):
            Optionally, the name of the body to use for any "M"
            codes that appear in the mask_desc.
        ignore_shadows (bool, optional):
            True to ignore any shadower or face constraints; default
            is False.

    Returns:
        numpy.array: Boolean bitmask containing the mask.
    """

    # Do not let a body block itself
    if target == blocker:
        blocker = None

    # Generate the new mask, with True means included
    if isinstance(target, str):
        primary_name = target.split(':')[0]
        if not oops.Body.exists(primary_name):
            return True

    (masker, shadower, face) = mask_desc

    excluded = np.zeros(backplane.shape, dtype='bool')

    # Handle maskers
    if "R" in masker and primary == "SATURN":
        excluded |= backplane.where_in_back(target, "SATURN_MAIN_RINGS").vals

    if "P" in masker:
        excluded |= backplane.where_in_back(target, primary).vals
        if primary == "PLUTO":
            excluded |= backplane.where_in_back(target, "CHARON").vals

    if "M" in masker and blocker is not None:
        excluded |= backplane.where_in_back(target, blocker).vals

    if not ignore_shadows:

        # Handle shadowers
        if "R" in shadower and primary == "SATURN":
            excluded |= backplane.where_inside_shadow(target,
                                                      "SATURN_MAIN_RINGS").vals

        if "P" in shadower:
            excluded |= backplane.where_inside_shadow(target, primary).vals
            if primary == "PLUTO":
                excluded |= backplane.where_inside_shadow(target, "CHARON").vals

        if "M" in shadower and blocker is not None:
            excluded |= backplane.where_inside_shadow(target, blocker).vals

        # Handle face selection
        if "D" in face:
            excluded |= backplane.where_antisunward(target).vals

        if "N" in face:
            excluded |= backplane.where_sunward(target).vals

#!!!!
# This function does does not handle gridless backplanes properly. This
# code fixes that, but the core problem should be fixed before this point.
    if np.any(excluded):
        return excluded
    if np.all(excluded):
        return True
    return False
