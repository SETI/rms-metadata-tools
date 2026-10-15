################################################################################
# geometry_support/masks.py - Excluded-pixel mask construction.
#
# Config-free: depends only on oops and numpy so it can be unit-tested without
# the host geometry_config plugin.
################################################################################
"""Excluded-pixel mask construction for geometry backplane processing."""
from dataclasses import dataclass
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
@dataclass(frozen=True)
class Pole:
    """The one pole of a body that could be in view, and its one-pixel backplane."""

    backplane: Any
    """A backplane whose meshgrid is the pixel containing the pole."""

    north: bool
    """True for the north pole, False for the south."""


#===============================================================================
def find_pole(backplane: Any, target: str | tuple[()]) -> Pole | None:
    """Locate the pole of the target that could be in view, if there is one.

    Every longitude meets at a pole, so when one is visible the coverage in
    longitude is complete. The samples of a meshgrid say little about this:
    they reach the pole region at scattered longitudes, and the largest gap
    between them is an accident of sampling. The pole itself is therefore
    located in the image, to be tested by pole_in_view against the mask of each
    column.

    Only the pole on the observer's side of the equatorial plane can be on the
    visible face, so the other is not considered.

    Parameters:
        backplane: The backplane defining the target surface.
        target: The name of the target body, optionally modified (e.g.
            "SATURN:RING"), or the empty tuple for quantities with no target body.

    Returns:
        The pole on the visible face of the body and within the area sampled by
        the backplane, with a backplane for its pixel; or None if there is none,
        if the target is modified, such as a ring, or if the observation cannot
        locate a surface point in its field of view.
    """
    if not isinstance(target, str) or ':' in target or not target_exists(target):
        return None

    # Only the pole on the observer's side of the equator can be visible
    sub_observer_lat = float(backplane.sub_observer_latitude(target).vals)
    if sub_observer_lat == 0.:
        return None
    north = sub_observer_lat > 0.

    obs = backplane.obs
    surface = oops.Body.lookup(target).surface
    try:
        pole_uv = obs.uv_from_coords(surface, (0., np.pi/2 if north else -np.pi/2))
    except NotImplementedError:
        return None

    # The pole is masked when it is on the far side of the body
    if np.any(pole_uv.mask):
        return None

    # The pole must be within the area sampled, including any border around the FOV
    uv = np.asarray(backplane.meshgrid.uv.vals, dtype=np.float64).reshape(-1, 2)
    uv_pole = np.asarray(pole_uv.vals, dtype=np.float64)
    if np.any(uv_pole < uv.min(axis=0)) or np.any(uv_pole > uv.max(axis=0)):
        return None

    meshgrid = oops.Meshgrid(obs.fov, oops.Pair(uv_pole[np.newaxis]))
    return Pole(oops.backplane.Backplane(obs, meshgrid), north)

#===============================================================================
def pole_in_view(pole: Pole | None, backplane: Any, target: str | tuple[()],
                 primary: str | None, mask_desc: tuple[str, str, str], *,
                 blocker: str | None = None,
                 ignore_shadows: bool = False) -> bool:
    """Determine whether a pole of the target is visible and outside a mask.

    The pole's backplane is shared by every mask tested against it, so the
    quantities those masks have in common are computed once.

    Parameters:
        pole: The pole that could be in view, from find_pole, or None.
        backplane: The backplane defining the target surface.
        target: The name of the target body.
        primary: Name of primary, e.g., "SATURN".
        mask_desc: A tuple (masker, shadower, face), as for
            construct_excluded_mask.
        blocker: Optionally, the name of the body to use for any "M" codes that
            appear in the mask_desc.
        ignore_shadows: True to ignore any shadower or face constraints; default
            is False.

    Returns:
        True if the pole is not excluded by the mask.
    """
    if pole is None:
        return False

    # A pole on the day side must have the Sun on its side of the equator
    if 'D' in mask_desc[2] and not ignore_shadows:
        sub_solar_lat = float(backplane.sub_solar_latitude(target).vals)
        if (sub_solar_lat > 0.) != pole.north or sub_solar_lat == 0.:
            return False

    excluded = construct_excluded_mask(pole.backplane, target, primary, mask_desc,
                                       blocker=blocker, ignore_shadows=ignore_shadows)
    return not np.any(excluded.vals)
