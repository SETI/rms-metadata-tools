################################################################################
# tests/test_geometry_masks.py: construct_excluded_mask (fake Backplane).
################################################################################
from typing import Any

import numpy as np
import numpy.typing as npt
import oops
import pytest

from metadata_tools.geometry_support import masks


@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every body name 'exist' (no SPICE registry available in tests)."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))


def _one_pixel(shape: tuple[int, int] = (4, 4)) -> npt.NDArray[np.bool_]:
    arr = np.zeros(shape, dtype=bool)
    arr[0, 0] = True
    return arr


#===============================================================================
# `fake_backplane` is the conftest-private FakeBackplane stub; typed as Any.
def test_planet_masker_ors_in_back(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.in_back[('IO', 'JUPITER')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('P', '', ''), ignore_shadows=True)
    assert isinstance(result, np.ndarray)
    assert result.sum() == 1


def test_ring_masker_only_for_saturn(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.in_back[('IO', 'SATURN_MAIN_RINGS')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'SATURN', ('R', '', ''), ignore_shadows=True)
    assert result.sum() == 1  # type: ignore[union-attr]


def test_moon_blocker_masker(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.in_back[('IO', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('M', '', ''),
        blocker='EUROPA', ignore_shadows=True)
    assert result.sum() == 1  # type: ignore[union-attr]


def test_target_cannot_block_itself(exists_true: None, fake_backplane: Any) -> None:
    # blocker == target -> blocker disabled, so no "M" masking is applied.
    fake_backplane.in_back[('EUROPA', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'EUROPA', 'JUPITER', ('M', '', ''),
        blocker='EUROPA', ignore_shadows=True)
    assert result is False


def test_ignore_shadows_skips_shadowers_and_faces(exists_true: None, fake_backplane: Any) -> None:
    # With ignore_shadows=True the antisunward face masker must not run.
    fake_backplane.antisunward['IO'] = np.ones((4, 4), dtype=bool)
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', '', 'D'), ignore_shadows=True)
    assert result is False


def test_day_face_masks_antisunward(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.antisunward['IO'] = np.ones((4, 4), dtype=bool)
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', '', 'D'), ignore_shadows=False)
    # An all-True mask is returned as the array itself; the trailing
    # `if np.all(excluded): return True` is unreachable (dead branch).
    assert isinstance(result, np.ndarray)
    assert result.all()


def test_shadowers_applied_when_not_ignored(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.inside_shadow[('IO', 'JUPITER')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', 'P', ''), ignore_shadows=False)
    assert result.sum() == 1  # type: ignore[union-attr]


def test_pluto_primary_also_masks_charon(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.in_back[('IO', 'PLUTO')] = _one_pixel()
    charon = np.zeros((4, 4), dtype=bool)
    charon[1, 1] = True
    fake_backplane.in_back[('IO', 'CHARON')] = charon
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'PLUTO', ('P', '', ''), ignore_shadows=True)
    assert result.sum() == 2  # type: ignore[union-attr]


def test_ring_shadower_for_saturn(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.inside_shadow[('IO', 'SATURN_MAIN_RINGS')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'SATURN', ('', 'R', ''), ignore_shadows=False)
    assert result.sum() == 1  # type: ignore[union-attr]


def test_moon_shadower(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.inside_shadow[('IO', 'EUROPA')] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', 'M', ''),
        blocker='EUROPA', ignore_shadows=False)
    assert result.sum() == 1  # type: ignore[union-attr]


def test_pluto_shadower_also_shadows_charon(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.inside_shadow[('IO', 'PLUTO')] = _one_pixel()
    charon = np.zeros((4, 4), dtype=bool)
    charon[2, 2] = True
    fake_backplane.inside_shadow[('IO', 'CHARON')] = charon
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'PLUTO', ('', 'P', ''), ignore_shadows=False)
    assert result.sum() == 2  # type: ignore[union-attr]


def test_night_face_masks_sunward(exists_true: None, fake_backplane: Any) -> None:
    fake_backplane.sunward['IO'] = _one_pixel()
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('', '', 'N'), ignore_shadows=False)
    assert result.sum() == 1  # type: ignore[union-attr]


def test_all_false_returns_python_false(exists_true: None, fake_backplane: Any) -> None:
    result = masks.construct_excluded_mask(
        fake_backplane, 'IO', 'JUPITER', ('P', '', ''), ignore_shadows=True)
    assert result is False


def test_nonexistent_target_returns_true(
        monkeypatch: pytest.MonkeyPatch, fake_backplane: Any) -> None:
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: False))
    result = masks.construct_excluded_mask(
        fake_backplane, 'NOPE', 'JUPITER', ('P', '', ''), ignore_shadows=True)
    assert result is True
