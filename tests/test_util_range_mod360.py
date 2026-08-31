################################################################################
# tests/test_util_range_mod360.py: _get_range_mod360 and the gap helper.
################################################################################
"""Tests for _get_range_mod360 and the ninety-percent gap helper."""
import numpy as np
import pytest

import metadata_tools.util as util


#===============================================================================
# _ninety_percent_gap_degrees
#===============================================================================
def test_ninety_percent_gap_uses_table_below_1000() -> None:
    """n below 1000 uses the lookup table.

    n=2 maps to 360 - NINETY_PERCENT_RANGE_DEGREES[2] (= 360 - 18).
    """
    assert util._ninety_percent_gap_degrees(2) == pytest.approx(342.0)


def test_ninety_percent_gap_power_law_above_1000() -> None:
    """n above 1000 follows the fitted power law."""
    expected = 1808. * 2000 ** (-0.912)
    assert util._ninety_percent_gap_degrees(2000) == pytest.approx(expected)


def test_ninety_percent_gap_scale_factor() -> None:
    """The scale factor multiplies the gap linearly."""
    base = util._ninety_percent_gap_degrees(50)
    assert util._ninety_percent_gap_degrees(50, scale=2.) == pytest.approx(2 * base)


#===============================================================================
# _get_range_mod360
#===============================================================================
def test_range_single_value() -> None:
    """A single value yields a degenerate [value, value] range."""
    assert util._get_range_mod360([7.0]) == [7.0, 7.0]


def test_range_wraparound_arc() -> None:
    """A tight arc straddling 0/360 returns the cyclic [lower, upper]."""
    result = util._get_range_mod360([350., 355., 5., 10.])
    assert result == [350.0, 10.0]


def test_range_full_coverage_via_diffmin() -> None:
    """Densely, evenly sampled angles with a tiny max gap give full coverage."""
    values = np.arange(0, 360, 2.0)
    assert util._get_range_mod360(values, width=1, diffmin=5) == [0., 360.]


def test_range_minus_180_alt_format() -> None:
    """alt_format='-180' maps the bounds into (-180, 180)."""
    result = util._get_range_mod360([350., 355., 5., 10.], alt_format='-180')
    assert result[0] == pytest.approx(-10.0)
    assert result[1] == pytest.approx(10.0)


def test_range_confident_gap_returns_arc() -> None:
    """Two clustered angles clear the 90% gap threshold; the narrow arc returns."""
    result = util._get_range_mod360([10., 20.])
    assert result == [10.0, 20.0]


def test_range_empty_returns_full_coverage() -> None:
    """With no values, nothing constrains the range, so full coverage returns."""
    assert util._get_range_mod360([]) == [0., 360.]


def test_range_empty_minus_180_returns_full_coverage() -> None:
    """An empty input with alt_format='-180' returns [-180, 180]."""
    assert util._get_range_mod360([], alt_format='-180') == [-180., 180.]
