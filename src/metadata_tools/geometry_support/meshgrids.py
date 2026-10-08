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
"""Default padding added to each side of a bounding box, as a fraction of its size.

The inventory treats every body as a sphere at the nominal pixel scale; the
margin absorbs what that approximation leaves out. A column that reaches
further from the body, as the limb columns do, states a larger margin of its
own with the MESHGRID_MARGIN keyword of its label template.
"""


#===============================================================================
def axis_samples(center: float, size: float, lower: float, upper: float,
                 sampling: float, min_samples: int,
                 margin: float = MARGIN) -> npt.NDArray[np.float64] | None:
    """Sample one axis of a bounding box, clipped to the limits of the FOV grid.

    The clipped box is sampled end to end at the pixel sampling density, or
    more finely if the body would otherwise get fewer than *min_samples*
    samples, however small it is. That minimum is counted across the body with
    the default margin -- or across the clipped box, if that is smaller -- so a
    larger margin adds samples around the body without spreading them thinner.

    Parameters:
        center: Coordinate of the center of the box, in pixels.
        size: Full size of the box, in pixels, before the margin is added.
        lower: Lower limit of the FOV grid.
        upper: Upper limit of the FOV grid.
        sampling: Pixel sampling density; the largest spacing allowed.
        min_samples: Minimum number of samples across the body.
        margin: Padding added to each side of the box, as a fraction of its
            size.

    Returns:
        The sample coordinates, or None if the box lies outside the limits.
    """
    half = size * (0.5 + margin)
    start = max(center - half, lower)
    stop = min(center + half, upper)
    # The negated test also rejects a NaN coordinate, as inventory() returns
    # for a body behind the camera.
    if not start < stop:
        return None

    extent = stop - start
    body = min(extent, size * (1 + 2*MARGIN))
    # The tolerance keeps a ratio that is a whole number in exact arithmetic
    # from being rounded up to the next one.
    intervals = max(math.ceil(extent / sampling - 1e-9),
                    math.ceil(extent / body * (min_samples - 1) - 1e-9))
    return np.linspace(start, stop, intervals + 1)

#===============================================================================
def box_meshgrid(fov_meshgrid: Any, center_uv: Any, size_uv: Any,
                 sampling: int, min_samples: int,
                 margin: float = MARGIN) -> tuple[Any, int] | None:
    """Build a meshgrid sampling the bounding box of one body.

    The box is clipped to the extent of the observation's FOV meshgrid, which
    already includes any border the host allows for pointing uncertainty.

    Parameters:
        fov_meshgrid: The meshgrid sampling the observation's whole FOV.
        center_uv: The (u,v) coordinates of the center of the body.
        size_uv: The (u,v) diameters of the body, in pixels.
        sampling: Pixel sampling density of the FOV meshgrid.
        min_samples: Minimum number of samples across the body, along each axis.
        margin: Padding added to each side of the box, as a fraction of its
            size.

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
                               sampling, min_samples, margin)
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
