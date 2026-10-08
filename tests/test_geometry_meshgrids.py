################################################################################
# tests/test_geometry_meshgrids.py: Body-specific meshgrid construction.
################################################################################
"""Tests for the meshgrids that sample one body's bounding box."""
from typing import Any

import numpy as np
import oops
import pytest

from metadata_tools.geometry_support import meshgrids

# An 800-pixel FOV with a 25-pixel border, as the GO_0xxx host samples it.
FOV = oops.fov.FlatFOV(1.e-5, (800, 800))


def _fov_meshgrid(sampling: float = 8.5) -> Any:
    """Return a meshgrid sampling the whole FOV and its border, v axis first."""
    return oops.Meshgrid.for_fov(FOV, -25., undersample=sampling, limit=825.0001,
                                 swap=True)


#===============================================================================
# axis_samples
#===============================================================================
def test_axis_samples_small_box_gets_the_minimum_count() -> None:
    """A box narrower than the minimum count allows is sampled more finely."""
    samples = meshgrids.axis_samples(100., 10., -25., 825., 8, 16)
    assert samples is not None
    assert len(samples) == 16
    # The 10% margin widens the 10-pixel box by one pixel on each side.
    assert samples[0] == pytest.approx(94.)
    assert samples[-1] == pytest.approx(106.)


def test_axis_samples_subpixel_box_is_resolved() -> None:
    """A body far smaller than a pixel still gets the minimum count across it."""
    samples = meshgrids.axis_samples(100.25, 0.01, -25., 825., 8, 16)
    assert samples is not None
    assert len(samples) == 16
    assert samples[0] == pytest.approx(100.244)
    assert samples[-1] == pytest.approx(100.256)


def test_axis_samples_large_box_keeps_the_pixel_sampling() -> None:
    """A large box is sampled no more coarsely than the pixel sampling density."""
    samples = meshgrids.axis_samples(400., 400., -25., 825., 8, 16)
    assert samples is not None
    assert (samples[0], samples[-1]) == pytest.approx((160., 640.))
    assert len(samples) == 61
    assert samples[1] - samples[0] == pytest.approx(8.)


def test_axis_samples_clips_before_counting() -> None:
    """The visible part of a box straddling the edge gets the minimum count."""
    samples = meshgrids.axis_samples(-25., 20., -25., 825., 8, 16)
    assert samples is not None
    assert len(samples) == 16
    assert (samples[0], samples[-1]) == pytest.approx((-25., -13.))


def test_axis_samples_wider_margin_keeps_the_density_of_the_body() -> None:
    """A wider margin adds samples around the body; it does not thin them out."""
    samples = meshgrids.axis_samples(100., 10., -25., 825., 8, 16, margin=1.5)
    assert samples is not None
    # A margin of 1.5 reaches 2 diameters, 4 radii, from the center.
    assert (samples[0], samples[-1]) == pytest.approx((80., 120.))
    # The spacing is that of the default box: 12 pixels in 15 intervals.
    assert len(samples) == 51
    assert samples[1] - samples[0] == pytest.approx(12. / 15.)


def test_axis_samples_wider_margin_of_a_large_body_keeps_the_pixel_sampling() -> None:
    """A large body's wider box is still sampled at the pixel sampling density."""
    samples = meshgrids.axis_samples(400., 200., -25., 825., 8, 16, margin=0.5)
    assert samples is not None
    assert (samples[0], samples[-1]) == pytest.approx((200., 600.))
    assert samples[1] - samples[0] == pytest.approx(8.)


@pytest.mark.parametrize('center', [-100., 900., float('nan')])
def test_axis_samples_outside_the_limits_is_none(center: float) -> None:
    """A box beyond the FOV, or with no usable position, has no samples."""
    assert meshgrids.axis_samples(center, 10., -25., 825., 8, 16) is None


#===============================================================================
# box_meshgrid
#===============================================================================
def test_box_meshgrid_samples_the_box() -> None:
    """The meshgrid spans the padded box, in the FOV of the FOV meshgrid."""
    grid = meshgrids.box_meshgrid(_fov_meshgrid(), (100., 300.), (10., 20.), 8, 16)
    assert grid is not None
    meshgrid, sampling = grid
    assert meshgrid.fov is FOV
    assert meshgrid.shape == (16, 16)
    uv = meshgrid.uv.vals
    assert (uv[..., 0].min(), uv[..., 0].max()) == pytest.approx((94., 106.))
    assert (uv[..., 1].min(), uv[..., 1].max()) == pytest.approx((288., 312.))
    # Like the FOV meshgrid, v varies along the first axis.
    assert np.all(uv[0, :, 1] == uv[0, 0, 1])
    # The spacing is below one pixel on u and above it on v; never less than 1.
    assert sampling == 2


def test_box_meshgrid_subpixel_sampling_is_at_least_one() -> None:
    """The reported sampling density of a sub-pixel grid is 1, never 0."""
    grid = meshgrids.box_meshgrid(_fov_meshgrid(), (100., 300.), (0.5, 0.5), 8, 16)
    assert grid is not None
    assert grid[1] == 1


def test_box_meshgrid_applies_the_margin() -> None:
    """A margin widens the box along both axes."""
    grid = meshgrids.box_meshgrid(_fov_meshgrid(), (100., 300.), (10., 10.), 8, 16,
                                  margin=1.5)
    assert grid is not None
    uv = grid[0].uv.vals
    assert grid[0].shape == (51, 51)
    assert (uv[..., 0].min(), uv[..., 0].max()) == pytest.approx((80., 120.))
    assert (uv[..., 1].min(), uv[..., 1].max()) == pytest.approx((280., 320.))


def test_box_meshgrid_outside_the_fov_is_none() -> None:
    """A body outside the FOV is left to the FOV meshgrid."""
    assert meshgrids.box_meshgrid(_fov_meshgrid(), (100., 2000.), (10., 10.), 8, 16) is None


def test_box_meshgrid_filling_the_fov_is_none() -> None:
    """A body covering the whole FOV is left to the FOV meshgrid."""
    assert meshgrids.box_meshgrid(_fov_meshgrid(), (400., 400.), (5000., 5000.), 8, 16) is None


def test_box_meshgrid_filling_a_coarse_fov_is_still_resampled() -> None:
    """A FOV meshgrid with too few samples is not reused for a body filling it."""
    grid = meshgrids.box_meshgrid(_fov_meshgrid(sampling=100.), (400., 400.),
                                  (5000., 5000.), 100, 16)
    assert grid is not None
    assert grid[0].shape == (16, 16)
