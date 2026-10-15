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
# find_pole and pole_in_view
#===============================================================================
class _FakeObs:
    """An observation that places each pole at a fixed pixel, or fails to."""

    def __init__(self, poles: dict[float, tuple[float, float] | None],
                 implemented: bool = True) -> None:
        self.fov = object()
        self.poles = poles
        self.implemented = implemented
        self.located: list[float] = []

    def uv_from_coords(self, surface: Any, coords: tuple[float, float]) -> Any:
        """Return the pixel of the pole at the given latitude, masked if hidden."""
        if not self.implemented:
            raise NotImplementedError
        self.located.append(coords[1])
        uv = self.poles.get(coords[1])
        if uv is None:
            return oops.Pair((0., 0.), True)
        return oops.Pair(uv)


@pytest.fixture
def pole_backplane(monkeypatch: pytest.MonkeyPatch, exists_true: None) -> Any:
    """Return a factory for a backplane sampling pixels 0 to 10 in u and v.

    The factory takes the observation and the sub-observer and sub-solar
    latitudes. The single-pixel backplane built at a pole records its pixel, and
    the mask applied there is excluded only for the pixels listed in the
    ``excluded`` attribute.
    """
    monkeypatch.setattr(oops.Body, 'lookup',
                        staticmethod(lambda name: types.SimpleNamespace(surface=None)))
    monkeypatch.setattr(oops, 'Meshgrid', lambda fov, uv: uv)
    monkeypatch.setattr(oops.backplane, 'Backplane',
                        lambda obs, meshgrid: types.SimpleNamespace(uv=meshgrid))
    excluded: list[tuple[float, float]] = []
    masked: list[tuple[str, str, str]] = []

    def _mask(backplane: Any, target: Any, primary: Any, mask_desc: Any,
              **kwargs: Any) -> polymath.Boolean:
        masked.append(mask_desc)
        uv = tuple(np.asarray(backplane.uv.vals).ravel())
        return polymath.Boolean(uv in excluded)

    monkeypatch.setattr(masks, 'construct_excluded_mask', _mask)
    grid = np.stack(np.meshgrid(np.arange(11.), np.arange(11.)), axis=-1)

    def _make(obs: _FakeObs, sub_observer_lat: float = -0.3,
              sub_solar_lat: float = -0.4) -> Any:
        return types.SimpleNamespace(
            obs=obs, meshgrid=types.SimpleNamespace(uv=oops.Pair(grid)),
            sub_observer_latitude=lambda target: oops.Scalar(sub_observer_lat),
            sub_solar_latitude=lambda target: oops.Scalar(sub_solar_lat),
            excluded=excluded, masked=masked)

    return _make


def _in_view(backplane: Any, mask_desc: tuple[str, str, str] = ('', '', '')) -> bool:
    """Locate the pole of SATURN and test it against one mask."""
    pole = masks.find_pole(backplane, 'SATURN')
    return masks.pole_in_view(pole, backplane, 'SATURN', 'SATURN', mask_desc)


def test_pole_in_view_when_a_pole_is_visible(pole_backplane: Any) -> None:
    """A pole on the visible face, inside the sampled area, is in view."""
    obs = _FakeObs({-np.pi/2: (4., 6.)})
    assert _in_view(pole_backplane(obs))


def test_only_the_pole_on_the_observers_side_is_located(pole_backplane: Any) -> None:
    """The pole across the equator from the observer is never considered."""
    obs = _FakeObs({np.pi/2: (4., 6.), -np.pi/2: (5., 5.)})
    assert _in_view(pole_backplane(obs, sub_observer_lat=-0.3))
    assert obs.located == [-np.pi/2]
    obs = _FakeObs({np.pi/2: (4., 6.)})
    assert not _in_view(pole_backplane(obs, sub_observer_lat=-0.3))
    obs = _FakeObs({np.pi/2: (4., 6.)})
    assert not _in_view(pole_backplane(obs, sub_observer_lat=0.))
    assert obs.located == []


def test_pole_on_far_side_is_not_in_view(pole_backplane: Any) -> None:
    """A pole hidden on the far side of the body is not in view."""
    obs = _FakeObs({-np.pi/2: None})
    assert not _in_view(pole_backplane(obs))


def test_pole_outside_sampled_area_is_not_in_view(pole_backplane: Any) -> None:
    """A pole beyond the area the backplane samples is not in view."""
    obs = _FakeObs({-np.pi/2: (5., -1.)})
    assert not _in_view(pole_backplane(obs))


def test_excluded_pole_is_not_in_view(pole_backplane: Any) -> None:
    """A pole excluded by the column's mask is not in view."""
    backplane = pole_backplane(_FakeObs({-np.pi/2: (2., 3.)}))
    assert _in_view(backplane)
    backplane.excluded.append((2., 3.))
    assert not _in_view(backplane)


def test_a_pole_in_darkness_fails_the_day_side_mask_untested(pole_backplane: Any) -> None:
    """With the Sun across the equator, the 'D' face excludes the pole at once."""
    backplane = pole_backplane(_FakeObs({-np.pi/2: (4., 6.)}), sub_solar_lat=0.2)
    assert not _in_view(backplane, ('RM', 'R', 'D'))
    assert backplane.masked == []
    assert _in_view(backplane, ('RM', 'R', ''))
    assert backplane.masked == [('RM', 'R', '')]


def test_one_pole_serves_every_mask(pole_backplane: Any) -> None:
    """A located pole is tested against each mask on its one backplane."""
    backplane = pole_backplane(_FakeObs({-np.pi/2: (4., 6.)}))
    pole = masks.find_pole(backplane, 'SATURN')
    assert pole is not None
    assert not pole.north
    for desc in (('RM', 'R', 'D'), ('RM', 'R', '')):
        assert masks.pole_in_view(pole, backplane, 'SATURN', 'SATURN', desc)
    assert backplane.masked == [('RM', 'R', 'D'), ('RM', 'R', '')]


def test_no_pole_for_rings_bodyless_targets_or_unlocatable_points(
        pole_backplane: Any) -> None:
    """A ring, the sky, and an observation without uv_from_coords have no pole."""
    backplane = pole_backplane(_FakeObs({-np.pi/2: (4., 6.)}))
    assert masks.find_pole(backplane, 'SATURN:RING') is None
    assert masks.find_pole(backplane, ()) is None
    assert masks.find_pole(pole_backplane(_FakeObs({}, implemented=False)),
                           'SATURN') is None
    assert not masks.pole_in_view(None, backplane, 'SATURN', 'SATURN', ('', '', ''))
