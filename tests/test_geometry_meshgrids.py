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
# fov_meshgrid
#===============================================================================
def test_fov_meshgrid_matches_the_grid_the_galileo_host_built() -> None:
    """A 25-pixel border reproduces the meshgrid the GO_0xxx host used to build."""
    # The host sampled -25 to 825 in 107 intervals of 850/107 pixels, end to end.
    grid = meshgrids.fov_meshgrid(FOV, 8, 25 * 1.e-5)
    expected = oops.Meshgrid.for_fov(FOV, -25., undersample=850/107, limit=825.0001,
                                     swap=True)
    assert grid.uv.vals.shape == (108, 108, 2)
    assert np.all(grid.uv.vals == expected.uv.vals)
    assert grid.fov is FOV


def test_fov_meshgrid_without_a_border_spans_the_fov() -> None:
    """With no border the samples run from one edge of the FOV to the other."""
    grid = meshgrids.fov_meshgrid(FOV, 8)
    uv = grid.uv.vals
    assert uv.shape == (101, 101, 2)
    assert uv.min() == pytest.approx(0.)
    assert uv.max() == pytest.approx(800.)


def test_fov_meshgrid_border_is_an_angle() -> None:
    """A summed FOV gets a border of proportionally fewer pixels."""
    summed = oops.fov.SubsampledFOV(FOV, 2)
    uv = meshgrids.fov_meshgrid(summed, 8, 25 * 1.e-5).uv.vals
    # 400 pixels and two 12.5-pixel borders, in 54 intervals of 425/54 pixels.
    assert uv.shape == (55, 55, 2)
    assert uv.min() == pytest.approx(-12.5)
    assert uv.max() == pytest.approx(412.5)


def test_fov_meshgrid_samples_each_axis_of_a_window() -> None:
    """A FOV trimmed to a cutout window is sampled over the window alone."""
    window = oops.fov.SliceFOV(FOV, (100, 200), (400, 96))
    uv = meshgrids.fov_meshgrid(window, 8, 25 * 1.e-5).uv.vals
    # v axis first: 96 + 50 pixels in 19 intervals, 400 + 50 pixels in 57.
    assert uv.shape == (20, 58, 2)
    assert uv[..., 0].min() == pytest.approx(-25.)
    assert uv[..., 1].min() == pytest.approx(-25.)
    assert uv[..., 0].max() == pytest.approx(425.)
    assert uv[..., 1].max() == pytest.approx(121.)


#===============================================================================
# cached_fov_meshgrid
#===============================================================================
def test_cached_fov_meshgrid_builds_each_fov_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The observations that share a FOV share its meshgrid."""
    built: list[Any] = []

    def _build(fov: Any, sampling: float, expand: float) -> str:
        built.append((fov, sampling, expand))
        return f'GRID{len(built)}'

    monkeypatch.setattr(meshgrids, 'fov_meshgrid', _build)
    other = oops.fov.SubsampledFOV(FOV, 2)
    cache: dict[Any, Any] = {}
    assert meshgrids.cached_fov_meshgrid(cache, FOV, 8, 1.e-4) == 'GRID1'
    assert meshgrids.cached_fov_meshgrid(cache, other, 8, 1.e-4) == 'GRID2'
    assert meshgrids.cached_fov_meshgrid(cache, FOV, 8, 1.e-4) == 'GRID1'
    assert built == [(FOV, 8, 1.e-4), (other, 8, 1.e-4)]
    # Each entry holds its FOV, so the identity it is keyed by stays unique.
    assert cache[id(FOV)][0] is FOV


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
