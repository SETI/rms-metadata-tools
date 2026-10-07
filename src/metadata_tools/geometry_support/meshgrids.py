################################################################################
# geometry_support/meshgrids.py - Body-specific meshgrid construction.
#
# Config-free: depends only on oops and numpy so it can be unit-tested without
# the host geometry_config plugin.
################################################################################
"""Meshgrids that sample the bounding box of one body, rather than the whole FOV."""
import math
from typing import Any

import numpy as np
import numpy.typing as npt
import oops

MARGIN = 0.1
"""Padding added to each side of a bounding box, as a fraction of its size.

The inventory treats every body as a sphere at the nominal pixel scale; the
margin absorbs what that approximation leaves out.
"""


#===============================================================================
def axis_samples(center: float, size: float, lower: float, upper: float,
                 sampling: float, min_samples: int) -> npt.NDArray[np.float64] | None:
    """Sample one axis of a bounding box, clipped to the limits of the FOV grid.

    The clipped box is sampled end to end at the pixel sampling density, but
    never with fewer than *min_samples* samples, however small it is.

    Parameters:
        center: Coordinate of the center of the box, in pixels.
        size: Full size of the box, in pixels, before the margin is added.
        lower: Lower limit of the FOV grid.
        upper: Upper limit of the FOV grid.
        sampling: Pixel sampling density; the largest spacing allowed.
        min_samples: Minimum number of samples.

    Returns:
        The sample coordinates, or None if the box lies outside the limits.
    """
    half = size * (0.5 + MARGIN)
    start = max(center - half, lower)
    stop = min(center + half, upper)
    # The negated test also rejects a NaN coordinate, as inventory() returns
    # for a body behind the camera.
    if not start < stop:
        return None

    samples = max(min_samples, math.ceil((stop - start) / sampling) + 1)
    return np.linspace(start, stop, samples)

#===============================================================================
def box_meshgrid(fov_meshgrid: Any, center_uv: Any, size_uv: Any,
                 sampling: int, min_samples: int) -> tuple[Any, int] | None:
    """Build a meshgrid sampling the bounding box of one body.

    The box is clipped to the extent of the observation's FOV meshgrid, which
    already includes any border the host allows for pointing uncertainty.

    Parameters:
        fov_meshgrid: The meshgrid sampling the observation's whole FOV.
        center_uv: The (u,v) coordinates of the center of the body.
        size_uv: The (u,v) diameters of the body, in pixels.
        sampling: Pixel sampling density of the FOV meshgrid.
        min_samples: Minimum number of samples across the box, along each axis.

    Returns:
        The meshgrid and its pixel sampling density, rounded to at least 1; or
        None if the FOV meshgrid is to be used instead: because the box lies
        outside the FOV, or because it covers a FOV that is already sampled
        finely enough.
    """
    uv = fov_meshgrid.uv.vals
    axes = []
    covers_fov = min(fov_meshgrid.shape) >= min_samples
    for i in (0, 1):
        lower = float(uv[..., i].min())
        upper = float(uv[..., i].max())
        samples = axis_samples(float(center_uv[i]), float(size_uv[i]), lower, upper,
                               sampling, min_samples)
        if samples is None:
            return None
        covers_fov &= bool(samples[0] == lower and samples[-1] == upper)
        axes.append(samples)

    # A body filling the FOV is sampled by the FOV meshgrid just as well, and
    # shares its backplanes with the other tables.
    if covers_fov:
        return None

    # The v axis comes first, like a FOV meshgrid built with swap=True; the
    # order has no bearing on the tabulated ranges.
    u, v = np.meshgrid(axes[0], axes[1])
    meshgrid = oops.Meshgrid(fov_meshgrid.fov, np.stack([u, v], axis=-1))
    step = max(axes[0][1] - axes[0][0], axes[1][1] - axes[1][0])
    return meshgrid, max(1, round(step))
