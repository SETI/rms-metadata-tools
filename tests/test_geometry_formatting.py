################################################################################
# tests/test_geometry_formatting.py: formatted_column + circle_coverage.
#
# These use real oops/polymath Scalars (which work without SPICE kernels) so the
# number formatting is exercised honestly rather than mock-shaped.
################################################################################
import numpy as np
import oops
import pytest

from metadata_tools.geometry_support import formats, formatting


#===============================================================================
# formatted_column
#===============================================================================
def test_two_value_degree_pair():
    fmt = formats.FORMAT_DICT['phase_angle']  # DEG, 2 values
    result = formatting.formatted_column(oops.Scalar([0.5, 1.0]), fmt, 8)
    assert result == '  28.648,  57.296'


def test_single_value_masked_uses_null():
    fmt = formats.FORMAT_DICT['center_coordinate']  # number_of_values == 1
    result = formatting.formatted_column(oops.Scalar(5.0, True), fmt, 8)
    assert result.strip() == '-99999.000'


def test_single_value_unmasked_is_mean():
    fmt = formats.FORMAT_DICT['center_coordinate']
    result = formatting.formatted_column(oops.Scalar([3.0, 5.0], False), fmt, 8)
    assert result.strip() == '4.000'


def test_fully_masked_two_value_pair_is_double_null():
    fmt = formats.FORMAT_DICT['distance']
    result = formatting.formatted_column(oops.Scalar([1., 2.], True), fmt, 8)
    assert result == '    -999.000,    -999.000'


def test_flag_360_routes_through_circle_coverage():
    fmt = formats.FORMAT_DICT['longitude']  # flag '360'
    result = formatting.formatted_column(
        oops.Scalar(np.array([0.1, 0.2, 0.3]), False), fmt, 8)
    assert result == '   0.000, 360.000'


def test_iso_route():
    fmt = formats.FORMAT_DICT['event_time']  # flag 'ISO'
    result = formatting.formatted_column(oops.Scalar([0.0, 60.0], False), fmt, 8)
    assert result == '"2000-01-01T11:59:28.000","2000-01-01T12:00:28.000"'


def test_nan_emits_warning_and_substitutes_null():
    fmt = formats.FORMAT_DICT['distance']
    with pytest.warns(UserWarning, match='NaN encountered'):
        result = formatting.formatted_column(
            oops.Scalar(np.array([np.nan, np.nan]), False), fmt, 8)
    assert result == '    -999.000,    -999.000'


def test_infinity_emits_warning_and_substitutes_null():
    fmt = formats.FORMAT_DICT['distance']
    with pytest.warns(UserWarning, match='infinity encountered'):
        result = formatting.formatted_column(
            oops.Scalar(np.array([np.inf, np.inf]), False), fmt, 8)
    assert result == '    -999.000,    -999.000'


def test_out_of_valid_range_becomes_null():
    fmt = formats.FORMAT_DICT['phase_angle']  # valid 0..180 deg
    # 10 rad -> ~573 deg, outside the valid maximum -> null substitution.
    result = formatting.formatted_column(
        oops.Scalar(np.array([10.0, 10.0]), False), fmt, 8)
    assert result == '-999.000,-999.000'


#===============================================================================
# circle_coverage
#===============================================================================
def test_circle_coverage_masked_scalar_is_double_null():
    assert formatting.circle_coverage(oops.Scalar([1., 2.], True), -999., 8) == \
        [-999., -999.]


def test_circle_coverage_unmasked_passes_through_range():
    # Dense even sampling -> full coverage [0, 360].
    angles = np.arange(0., 360., 3.0)
    assert formatting.circle_coverage(angles, -999., 8) == [0., 360.]


def test_circle_coverage_minus_180_flag():
    # With the smoothing width sampling+1, the four clustered angles smear into
    # apparent full coverage, reported in the (-180, 180) convention.
    result = formatting.circle_coverage(
        oops.Scalar(np.array([350., 355., 5., 10.]), False), -999., 8, flag='-180')
    assert result == [-180., 180.]


def test_circle_coverage_partially_masked_scalar():
    # antimask selects the two unmasked angles; the helper still runs.
    scalar = oops.Scalar(np.array([10., 20., 200., 210.]),
                         np.array([False, False, True, True]))
    assert formatting.circle_coverage(scalar, -999., 8) == [0., 360.]


def test_overflow_clips_and_warns():
    fmt = formats.FORMAT_DICT['resolution']  # width 10, overflow %10.4e
    with pytest.warns(UserWarning, match='clipped to'):
        result = formatting.formatted_column(
            oops.Scalar(np.array([1e120, 1e120]), False), fmt, 8)
    assert result == '9.9900e+99,9.9900e+99'
