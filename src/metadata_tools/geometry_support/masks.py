################################################################################
# geometry_support/masks.py - Excluded-pixel mask construction.
#
# Config-free: depends only on oops and numpy so it can be unit-tested without
# the host geometry_config plugin.
################################################################################
from typing import Any

import numpy as np
import numpy.typing as npt
import oops


#===============================================================================
def construct_excluded_mask(backplane: Any, target: str, primary: str | None,
                            mask_desc: tuple[str, str, str], *,
                            blocker: str | None = None,
                            ignore_shadows: bool = True) -> npt.NDArray[np.bool_] | bool:
    """Return a mask of excluded pixels for the given target.

    The mask is built from the specified target, maskers and shadowers.

    Parameters:
        backplane: The backplane defining the target surface.
        target: The name of the target surface.
        primary: Name of primary, e.g., "SATURN".
        mask_desc: A tuple (masker, shadower, face), where masker is a string
            identifying what surfaces can obscure the target, formed by
            concatenating "P" to let the planet obscure the target, "R" to let
            the rings obscure the target, and "M" to let the blocker body
            obscure the target; shadower is a string identifying what surfaces
            can shadow the target, formed by concatenating "P" to let the planet
            shadow the target, "R" to let the rings shadow the target, and "M"
            to let the blocker body shadow the target; and face is a string
            identifying which face(s) of the surface to include, where "D"
            includes only the day side of the target, "N" includes only the
            night side of the target, and "" includes both faces of the target.
        blocker: Optionally, the name of the body to use for any "M" codes that
            appear in the mask_desc.
        ignore_shadows: True to ignore any shadower or face constraints; default
            is False.

    Returns:
        Boolean bitmask containing the mask.
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
# This function does not handle gridless backplanes properly. This
# code fixes that, but the core problem should be fixed before this point.
    if np.any(excluded):
        return excluded
    return bool(np.all(excluded))
