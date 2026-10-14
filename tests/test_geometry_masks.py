################################################################################
# tests/test_geometry_masks.py: construct_excluded_mask (fake Backplane).
################################################################################
"""Tests for construct_excluded_mask using the conftest FakeBackplane."""
import types
from typing import Any

import numpy as np
import numpy.typing as npt
import oops
import polymath
import pytest

from metadata_tools.geometry_support import masks


def _one_pixel(shape: tuple[int, int] = (4, 4)) -> npt.NDArray[np.bool_]:
    """Return an all-False boolean array with one True pixel at (0, 0).

    Returns:
        A boolean array of the given shape with only [0, 0] set.
    """
    arr = np.zeros(shape, dtype=bool)
    arr[0, 0] = True
    return arr


#===============================================================================
def test_bodyless_target_skips_body_lookup(monkeypatch: pytest.MonkeyPatch,
                                           fake_backplane: Any) -> None:
    """The sky table's empty-tuple target is not looked up as a body.

    Regression: the sky columns are keyed ('right_ascension', ()), so the target
    is (), which has no .split and names no body.
    """
    def _no_lookup(name: str) -> bool:
        raise AssertionError(f'unexpected body lookup: {name!r}')

    monkeypatch.setattr(oops.Body, 'exists', staticmethod(_no_lookup))
    result = masks.construct_excluded_mask(fake_backplane, (), None, ('', '', ''))
    assert isinstance(result, polymath.Boolean)
    assert not np.any(result.vals)


#===============================================================================
# `fake_backplane` is the conftest-private FakeBackplane stub; typed as Any.
def test_planet_masker_ors_in_back(exists_true: None, fake_backplane: Any) -> None:
    """The 'P' masker ORs in the target-behind-primary pixels."""
    fake_backplane.in_back[('IO', 'JUPITER')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('P', '', ''), ignore_shadows=True)
    assert isinstance(result, polymath.Boolean)
    assert np.asarray(result.vals).sum() == 1


def test_ring_masker_only_for_saturn(exists_true: None, fake_backplane: Any) -> None:
    """The 'R' masker applies the main-ring obscuration for primary SATURN."""
    fake_backplane.in_back[('IO', 'SATURN_MAIN_RINGS')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'SATURN', ('R', '', ''), ignore_shadows=True)
    assert np.asarray(result.vals).sum() == 1


def test_moon_blocker_masker(exists_true: None, fake_backplane: Any) -> None:
    """The 'M' masker applies the blocker moon's obscuration."""
    fake_backplane.in_back[('IO', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('M', '', ''),
        blocker='EUROPA', ignore_shadows=True)
    assert np.asarray(result.vals).sum() == 1


def test_target_cannot_block_itself(exists_true: None, fake_backplane: Any) -> None:
    """A blocker equal to the target is disabled, so no 'M' masking applies."""
    fake_backplane.in_back[('EUROPA', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'EUROPA', 'JUPITER', ('M', '', ''),
        blocker='EUROPA', ignore_shadows=True)
    assert not np.any(result.vals)


def test_ignore_shadows_skips_shadowers_and_faces(exists_true: None, fake_backplane: Any) -> None:
    """With ignore_shadows=True the antisunward face masker does not run."""
    fake_backplane.antisunward['IO'] = np.ones((4, 4), dtype=bool)
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', '', 'D'), ignore_shadows=True)
    assert not np.any(result.vals)


def test_day_face_masks_antisunward(exists_true: None, fake_backplane: Any) -> None:
    """The 'D' face masker masks antisunward pixels when shadows are honored."""
    fake_backplane.antisunward['IO'] = np.ones((4, 4), dtype=bool)
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', '', 'D'), ignore_shadows=False)
    assert isinstance(result, polymath.Boolean)
    assert result.vals is True


def test_shadowers_applied_when_not_ignored(exists_true: None, fake_backplane: Any) -> None:
    """The 'P' shadower masks pixels inside the primary's shadow."""
    fake_backplane.inside_shadow[('IO', 'JUPITER')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', 'P', ''), ignore_shadows=False)
    assert np.asarray(result.vals).sum() == 1


def test_pluto_primary_also_masks_charon(exists_true: None, fake_backplane: Any) -> None:
    """A PLUTO primary masker also masks pixels behind CHARON."""
    fake_backplane.in_back[('IO', 'PLUTO')] = _one_pixel()
    charon = np.zeros((4, 4), dtype=bool)
    charon[1, 1] = True
    fake_backplane.in_back[('IO', 'CHARON')] = charon
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'PLUTO', ('P', '', ''), ignore_shadows=True)
    assert np.asarray(result.vals).sum() == 2


def test_ring_shadower_for_saturn(exists_true: None, fake_backplane: Any) -> None:
    """The 'R' shadower masks pixels inside the main rings' shadow."""
    fake_backplane.inside_shadow[('IO', 'SATURN_MAIN_RINGS')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'SATURN', ('', 'R', ''), ignore_shadows=False)
    assert np.asarray(result.vals).sum() == 1


def test_moon_shadower(exists_true: None, fake_backplane: Any) -> None:
    """The 'M' shadower masks pixels inside the blocker moon's shadow."""
    fake_backplane.inside_shadow[('IO', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', 'M', ''),
        blocker='EUROPA', ignore_shadows=False)
    assert np.asarray(result.vals).sum() == 1


def test_pluto_shadower_also_shadows_charon(exists_true: None, fake_backplane: Any) -> None:
    """A PLUTO shadower also masks pixels inside CHARON's shadow."""
    fake_backplane.inside_shadow[('IO', 'PLUTO')] = _one_pixel()
    charon = np.zeros((4, 4), dtype=bool)
    charon[2, 2] = True
    fake_backplane.inside_shadow[('IO', 'CHARON')] = charon
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'PLUTO', ('', 'P', ''), ignore_shadows=False)
    assert np.asarray(result.vals).sum() == 2


def test_night_face_masks_sunward(exists_true: None, fake_backplane: Any) -> None:
    """The 'N' face masker masks the sunward pixels."""
    fake_backplane.sunward['IO'] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', '', 'N'), ignore_shadows=False)
    assert np.asarray(result.vals).sum() == 1


def test_all_false_returns_boolean_false(exists_true: None, fake_backplane: Any) -> None:
    """With nothing masked, the result is an all-False Boolean."""
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('P', '', ''), ignore_shadows=True)
    assert isinstance(result, polymath.Boolean)
    assert not np.any(result.vals)


def test_nonexistent_target_returns_boolean_true(
        monkeypatch: pytest.MonkeyPatch, fake_backplane: Any) -> None:
    """A target unknown to oops.Body yields an all-True (fully excluded) mask."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: False))
    result = masks.construct_excluded_mask(
        fake_backplane, 'NOPE', 'JUPITER', ('P', '', ''), ignore_shadows=True)
    assert isinstance(result, polymath.Boolean)
    assert result.vals is True


#===============================================================================
# pole_in_view
#===============================================================================
class _FakeObs:
    """An observation that places each pole at a fixed pixel, or fails to."""

    def __init__(self, poles: dict[float, tuple[float, float] | None],
                 implemented: bool = True) -> None:
        self.fov = object()
        self.poles = poles
        self.implemented = implemented

    def uv_from_coords(self, surface: Any, coords: tuple[float, float]) -> Any:
        """Return the pixel of the pole at the given latitude, masked if hidden."""
        if not self.implemented:
            raise NotImplementedError
        uv = self.poles[coords[1]]
        if uv is None:
            return oops.Pair((0., 0.), True)
        return oops.Pair(uv)


@pytest.fixture
def pole_backplane(monkeypatch: pytest.MonkeyPatch, exists_true: None) -> Any:
    """Return a factory for a backplane sampling pixels 0 to 10 in u and v.

    The single-pixel backplane built at a pole is replaced by a marker, and the
    mask applied there is excluded only for the latitudes listed in its
    ``excluded`` attribute.
    """
    monkeypatch.setattr(oops.Body, 'lookup',
                        staticmethod(lambda name: types.SimpleNamespace(surface=None)))
    monkeypatch.setattr(oops, 'Meshgrid', lambda fov, uv: uv)
    monkeypatch.setattr(oops.backplane, 'Backplane',
                        lambda obs, meshgrid: types.SimpleNamespace(uv=meshgrid))
    excluded: list[tuple[float, float]] = []

    def _mask(backplane: Any, *args: Any, **kwargs: Any) -> polymath.Boolean:
        uv = tuple(np.asarray(backplane.uv.vals).ravel())
        return polymath.Boolean(uv in excluded)

    monkeypatch.setattr(masks, 'construct_excluded_mask', _mask)
    grid = np.stack(np.meshgrid(np.arange(11.), np.arange(11.)), axis=-1)

    def _make(obs: _FakeObs) -> Any:
        return types.SimpleNamespace(
            obs=obs, meshgrid=types.SimpleNamespace(uv=oops.Pair(grid)),
            excluded=excluded)

    return _make


def test_pole_in_view_when_a_pole_is_visible(pole_backplane: Any) -> None:
    """A pole on the visible face, inside the sampled area, is in view."""
    obs = _FakeObs({np.pi/2: None, -np.pi/2: (4., 6.)})
    assert masks.pole_in_view(pole_backplane(obs), 'SATURN', 'SATURN', ('', '', ''))


def test_pole_on_far_side_is_not_in_view(pole_backplane: Any) -> None:
    """Poles on the far side of the body are not in view."""
    obs = _FakeObs({np.pi/2: None, -np.pi/2: None})
    assert not masks.pole_in_view(pole_backplane(obs), 'SATURN', 'SATURN', ('', '', ''))


def test_pole_outside_sampled_area_is_not_in_view(pole_backplane: Any) -> None:
    """A pole beyond the area the backplane samples is not in view."""
    obs = _FakeObs({np.pi/2: (12., 5.), -np.pi/2: (5., -1.)})
    assert not masks.pole_in_view(pole_backplane(obs), 'SATURN', 'SATURN', ('', '', ''))


def test_excluded_pole_is_not_in_view(pole_backplane: Any) -> None:
    """A pole excluded by the column's mask is not in view, but the other may be."""
    obs = _FakeObs({np.pi/2: (2., 3.), -np.pi/2: (7., 8.)})
    backplane = pole_backplane(obs)
    backplane.excluded.append((2., 3.))
    assert masks.pole_in_view(backplane, 'SATURN', 'SATURN', ('', '', 'D'))
    backplane.excluded.append((7., 8.))
    assert not masks.pole_in_view(backplane, 'SATURN', 'SATURN', ('', '', 'D'))


def test_pole_in_view_is_false_for_rings_and_bodyless_targets(pole_backplane: Any) -> None:
    """A modified target, such as a ring, and the sky have no poles to test."""
    obs = _FakeObs({np.pi/2: (4., 6.), -np.pi/2: (4., 6.)})
    assert not masks.pole_in_view(pole_backplane(obs), 'SATURN:RING', 'SATURN',
                                  ('', '', ''))
    assert not masks.pole_in_view(pole_backplane(obs), (), None, ('', '', ''))


def test_pole_in_view_is_false_when_the_observation_cannot_locate_it(
        pole_backplane: Any) -> None:
    """An observation without uv_from_coords leaves the coverage to the samples."""
    obs = _FakeObs({}, implemented=False)
    assert not masks.pole_in_view(pole_backplane(obs), 'SATURN', 'SATURN', ('', '', ''))
