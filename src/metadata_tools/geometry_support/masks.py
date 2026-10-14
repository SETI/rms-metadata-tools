################################################################################
# geometry_support/masks.py - Excluded-pixel mask construction.
#
# Config-free: depends only on oops and numpy so it can be unit-tested without
# the host geometry_config plugin.
################################################################################
"""Excluded-pixel mask construction for geometry backplane processing."""
from typing import Any

import numpy as np
import oops
import polymath


#===============================================================================
def target_exists(target: str | tuple[()]) -> bool:
    """Determine whether a backplane target names a body registered with oops.

    Parameters:
        target: The name of the target surface, optionally modified (e.g.
            "SATURN:RING"), or the empty tuple for quantities with no target
            body.

    Returns:
        False only for a named target whose body is not registered; e.g. the
        ring system of a planet that has none. A body-less target has no body
        to look up.
    """
    if isinstance(target, str):
        return bool(oops.Body.exists(target.split(':')[0]))
    return True

#===============================================================================
def construct_excluded_mask(backplane: Any, target: str | tuple[()], primary: str | None,
                            mask_desc: tuple[str, str, str], *,
                            blocker: str | None = None,
                            ignore_shadows: bool = False) -> polymath.Boolean:
    """Return a mask of excluded pixels for the given target.

    The mask is built from the specified target, maskers and shadowers.

    Parameters:
        backplane: The backplane defining the target surface.
        target: The name of the target surface, or the empty tuple for
            quantities with no target body (e.g. the sky table's right ascension
            and declination, keyed ``('right_ascension', ())``).
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
        polymath.Boolean mask; scalar True/False for all-excluded/none-excluded,
        array otherwise.
    """

    # Do not let a body block itself
    if target == blocker:
        blocker = None

    # Generate the new mask, with True means included.
    if not target_exists(target):
        return polymath.Boolean(True)

    (masker, shadower, face) = mask_desc

    # backplane.meshgrid.shape works for every oops version; Backplane.shape went
    # private (_shape) in oops >= 0.3
    excluded = np.zeros(backplane.meshgrid.shape, dtype='bool')

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

    if not np.any(excluded):
        return polymath.Boolean(False)
    if np.all(excluded):
        return polymath.Boolean(True)
    return polymath.Boolean(excluded)

#===============================================================================
def pole_in_view(backplane: Any, target: str | tuple[()], primary: str | None,
                 mask_desc: tuple[str, str, str], *,
                 blocker: str | None = None,
                 ignore_shadows: bool = False) -> bool:
    """Determine whether a pole of the target is visible within a backplane.

    Every longitude meets at a pole, so when one is visible the coverage in
    longitude is complete. The samples of a meshgrid say little about this:
    they reach the pole region at scattered longitudes, and the largest gap
    between them is an accident of sampling. The pole itself is therefore
    located in the image and tested against the same mask as the samples.

    Parameters:
        backplane: The backplane defining the target surface.
        target: The name of the target body, optionally modified (e.g.
            "SATURN:RING"), or the empty tuple for quantities with no target body.
        primary: Name of primary, e.g., "SATURN".
        mask_desc: A tuple (masker, shadower, face), as for
            construct_excluded_mask.
        blocker: Optionally, the name of the body to use for any "M" codes that
            appear in the mask_desc.
        ignore_shadows: True to ignore any shadower or face constraints; default
            is False.

    Returns:
        True if either pole of the target body lies on its visible face, within
        the area sampled by the backplane, and is not excluded by the mask.
        False for a modified target, such as a ring, and for an observation that
        cannot locate a surface point in its field of view.
    """
    if not isinstance(target, str) or ':' in target or not target_exists(target):
        return False

    obs = backplane.obs
    surface = oops.Body.lookup(target).surface

    # The area sampled, including any border around the FOV
    uv = np.asarray(backplane.meshgrid.uv.vals, dtype=np.float64).reshape(-1, 2)
    uv_min = uv.min(axis=0)
    uv_max = uv.max(axis=0)

    for lat in (np.pi/2, -np.pi/2):
        try:
            pole_uv = obs.uv_from_coords(surface, (0., lat))
        except NotImplementedError:
            return False

        # The pole is masked when it is on the far side of the body
        if np.any(pole_uv.mask):
            continue
        uv_pole = np.asarray(pole_uv.vals, dtype=np.float64)
        if np.any(uv_pole < uv_min) or np.any(uv_pole > uv_max):
            continue

        # Apply the mask to the pixel containing the pole
        meshgrid = oops.Meshgrid(obs.fov, oops.Pair(uv_pole[np.newaxis]))
        pole_backplane = oops.backplane.Backplane(obs, meshgrid)
        excluded = construct_excluded_mask(pole_backplane, target, primary, mask_desc,
                                           blocker=blocker,
                                           ignore_shadows=ignore_shadows)
        if not np.any(excluded.vals):
            return True

    return False
