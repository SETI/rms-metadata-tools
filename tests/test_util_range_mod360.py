################################################################################
# tests/test_util_range_mod360.py: _get_range_mod360 and the gap helper.
################################################################################
import numpy as np
import pytest

import metadata_tools.util as util


#===============================================================================
# _ninety_percent_gap_degrees
#===============================================================================
def test_ninety_percent_gap_uses_table_below_1000():
    # n=2 maps to 360 - NINETY_PERCENT_RANGE_DEGREES[2] (= 360 - 18).
    assert util._ninety_percent_gap_degrees(2) == pytest.approx(342.0)


def test_ninety_percent_gap_power_law_above_1000():
    expected = 1808. * 2000 ** (-0.912)
    assert util._ninety_percent_gap_degrees(2000) == pytest.approx(expected)


def test_ninety_percent_gap_scale_factor():
    base = util._ninety_percent_gap_degrees(50)
    assert util._ninety_percent_gap_degrees(50, scale=2.) == pytest.approx(2 * base)


#===============================================================================
# _get_range_mod360
#===============================================================================
def test_range_single_value():
    assert util._get_range_mod360([7.0]) == [7.0, 7.0]


def test_range_wraparound_arc():
    # A tight arc straddling 0/360 returns the cyclic [lower, upper].
    result = util._get_range_mod360([350., 355., 5., 10.])
    assert result == [350.0, 10.0]


def test_range_full_coverage_via_diffmin():
    # Densely, evenly sampled angles with a tiny max gap -> full coverage.
    values = np.arange(0, 360, 2.0)
    assert util._get_range_mod360(values, width=1, diffmin=5) == [0., 360.]


def test_range_minus_180_alt_format():
    result = util._get_range_mod360([350., 355., 5., 10.], alt_format='-180')
    # Lower/upper mapped into (-180, 180).
    assert result[0] == pytest.approx(-10.0)
    assert result[1] == pytest.approx(10.0)


def test_range_confident_gap_returns_arc():
    # Two clustered angles: the large gap clears the 90% confidence threshold,
    # so the narrow arc is returned rather than full coverage.
    result = util._get_range_mod360([10., 20.])
    assert result == [10.0, 20.0]


def test_range_empty_raises_indexerror():
    # The docstring does not promise this; current behavior is an IndexError
    # because values[0] is accessed on an empty array.
    with pytest.raises(IndexError):
        util._get_range_mod360([])
