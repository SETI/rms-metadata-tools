################################################################################
# tests/test_geometry_masks.py: construct_excluded_mask (fake Backplane).
################################################################################
"""Tests for construct_excluded_mask using the conftest FakeBackplane."""
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
# `fake_backplane` is the conftest-private FakeBackplane stub; typed as Any.
def test_planet_masker_ors_in_back(exists_true: None, fake_backplane: Any) -> None:
    """The 'P' masker ORs in the target-behind-primary pixels."""
    fake_backplane.in_back[('IO', 'JUPITER')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('P', '', ''), ignore_shadows=True)
    assert isinstance(result, polymath.Boolean)
    assert result.vals.sum() == 1


def test_ring_masker_only_for_saturn(exists_true: None, fake_backplane: Any) -> None:
    """The 'R' masker applies the main-ring obscuration for primary SATURN."""
    fake_backplane.in_back[('IO', 'SATURN_MAIN_RINGS')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'SATURN', ('R', '', ''), ignore_shadows=True)
    assert result.vals.sum() == 1


def test_moon_blocker_masker(exists_true: None, fake_backplane: Any) -> None:
    """The 'M' masker applies the blocker moon's obscuration."""
    fake_backplane.in_back[('IO', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('M', '', ''),
        blocker='EUROPA', ignore_shadows=True)
    assert result.vals.sum() == 1


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
    assert result.vals.sum() == 1


def test_pluto_primary_also_masks_charon(exists_true: None, fake_backplane: Any) -> None:
    """A PLUTO primary masker also masks pixels behind CHARON."""
    fake_backplane.in_back[('IO', 'PLUTO')] = _one_pixel()
    charon = np.zeros((4, 4), dtype=bool)
    charon[1, 1] = True
    fake_backplane.in_back[('IO', 'CHARON')] = charon
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'PLUTO', ('P', '', ''), ignore_shadows=True)
    assert result.vals.sum() == 2


def test_ring_shadower_for_saturn(exists_true: None, fake_backplane: Any) -> None:
    """The 'R' shadower masks pixels inside the main rings' shadow."""
    fake_backplane.inside_shadow[('IO', 'SATURN_MAIN_RINGS')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'SATURN', ('', 'R', ''), ignore_shadows=False)
    assert result.vals.sum() == 1


def test_moon_shadower(exists_true: None, fake_backplane: Any) -> None:
    """The 'M' shadower masks pixels inside the blocker moon's shadow."""
    fake_backplane.inside_shadow[('IO', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', 'M', ''),
        blocker='EUROPA', ignore_shadows=False)
    assert result.vals.sum() == 1


def test_pluto_shadower_also_shadows_charon(exists_true: None, fake_backplane: Any) -> None:
    """A PLUTO shadower also masks pixels inside CHARON's shadow."""
    fake_backplane.inside_shadow[('IO', 'PLUTO')] = _one_pixel()
    charon = np.zeros((4, 4), dtype=bool)
    charon[2, 2] = True
    fake_backplane.inside_shadow[('IO', 'CHARON')] = charon
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'PLUTO', ('', 'P', ''), ignore_shadows=False)
    assert result.vals.sum() == 2


def test_night_face_masks_sunward(exists_true: None, fake_backplane: Any) -> None:
    """The 'N' face masker masks the sunward pixels."""
    fake_backplane.sunward['IO'] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', '', 'N'), ignore_shadows=False)
    assert result.vals.sum() == 1


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
