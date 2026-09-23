################################################################################
# tests/test_geometry_formatting.py: formatted_column + circle_coverage.
#
# These use real oops/polymath Scalars (which work without SPICE kernels) so the
# number formatting is exercised honestly rather than mock-shaped.
################################################################################
"""Tests for formatted_column and circle_coverage using real oops Scalars."""
import types
from collections.abc import Callable
from typing import Any

import numpy as np
import oops
import pytest

import metadata_tools.common as com
from metadata_tools.geometry_support import formatting


#===============================================================================
# formatted_column
#===============================================================================
def test_two_value_degree_pair(make_column: Callable[..., Any]) -> None:
    """A two-value degree column formats both radian values converted to degrees."""
    col = make_column(flag='DEG', valid_minimum=0., valid_maximum=180.)
    result = formatting.formatted_column(oops.Scalar([0.5, 1.0]), col.stubs, 8)
    assert result == '  28.648,  57.296'


def test_single_value_masked_uses_null(make_column: Callable[..., Any]) -> None:
    """A masked single-value column formats as the null value."""
    col = make_column(names=['CENTER_X_COORDINATE'], flag='', overflow='%12.5e',
                      width=12, print_format='%12.3f', null_value=-99999.)
    result = formatting.formatted_column(oops.Scalar(5.0, True), col.stubs, 8)
    assert result.strip() == '-99999.000'


def test_single_value_unmasked_is_mean(make_column: Callable[..., Any]) -> None:
    """A single-value column formats the mean of the unmasked values."""
    col = make_column(names=['CENTER_X_COORDINATE'], flag='', overflow='%12.5e',
                      width=12, print_format='%12.3f', null_value=-99999.)
    result = formatting.formatted_column(oops.Scalar([3.0, 5.0], False), col.stubs, 8)
    assert result.strip() == '4.000'


def test_fully_masked_two_value_pair_is_double_null(make_column: Callable[..., Any]) -> None:
    """A fully masked two-value column formats as a null pair."""
    col = make_column(flag='', overflow='%12.5e', width=12, print_format='%12.3f')
    result = formatting.formatted_column(oops.Scalar([1., 2.], True), col.stubs, 8)
    assert result == '    -999.000,    -999.000'


def test_flag_360_routes_through_circle_coverage(make_column: Callable[..., Any]) -> None:
    """The '360' flag reports cyclic coverage via circle_coverage."""
    col = make_column(flag='360', valid_minimum=0., valid_maximum=360.)
    result = formatting.formatted_column(
        oops.Scalar(np.array([0.1, 0.2, 0.3]), False), col.stubs, 8)
    assert result == '   0.000, 360.000'


def test_flag_minus_180_routes_through_circle_coverage(
        make_column: Callable[..., Any]) -> None:
    """The '-180' flag converts to degrees and reports coverage in (-180, 180)."""
    col = make_column(flag='-180', valid_minimum=-180., valid_maximum=180.)
    result = formatting.formatted_column(
        oops.Scalar(np.array([0.1, 0.2, 0.3]), False), col.stubs, 8)
    assert result == '-180.000, 180.000'


def test_iso_route(make_column: Callable[..., Any]) -> None:
    """The 'ISO' flag formats times as quoted ISO date strings."""
    col = make_column(flag='ISO', overflow='%25s', width=25, print_format='%25s',
                      null_value='NA')
    result = formatting.formatted_column(oops.Scalar([0.0, 60.0], False), col.stubs, 8)
    assert result == '"2000-01-01T11:59:28.000","2000-01-01T12:00:28.000"'


def test_string_null_fills_every_slot(make_column: Callable[..., Any]) -> None:
    """A string null is written once per slot, not once per column.

    Emitting a single field for a two-slot column would short the row and shift
    every column after it. The null arrives unquoted from the template (the
    label says NULL_CONSTANT = "NA"), and must format identically either way.
    """
    col = make_column(flag='ISO', overflow='%25s', width=25, print_format='%25s',
                      null_value='NA')
    unquoted = formatting.formatted_column('NA', col.stubs, 8)
    quoted = formatting.formatted_column('"NA"', col.stubs, 8)
    assert unquoted == quoted
    assert unquoted.split(',') == ['"NA' + ' ' * 21 + '"'] * 2


@pytest.fixture
def logged_warnings(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture the global logger's warnings as formatted strings.

    Returns:
        The list into which each warning message is appended.
    """
    warnings: list[str] = []
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            warning=lambda msg, *a: warnings.append(msg % a)))
    return warnings


def test_nan_logs_warning_and_substitutes_null(
        make_column: Callable[..., Any], logged_warnings: list[str]) -> None:
    """NaN values are logged per column and replaced by the null value."""
    col = make_column(flag='', overflow='%12.5e', width=12, print_format='%12.3f')
    result = formatting.formatted_column(
        oops.Scalar(np.array([np.nan, np.nan]), False), col.stubs, 8)
    assert result == '    -999.000,    -999.000'
    assert logged_warnings == ['NaN encountered in MINIMUM_PHASE_ANGLE',
                               'NaN encountered in MAXIMUM_PHASE_ANGLE']


def test_infinity_logs_warning_and_substitutes_null(
        make_column: Callable[..., Any], logged_warnings: list[str]) -> None:
    """Infinite values are logged per column and replaced by the null value."""
    col = make_column(flag='', overflow='%12.5e', width=12, print_format='%12.3f')
    result = formatting.formatted_column(
        oops.Scalar(np.array([np.inf, np.inf]), False), col.stubs, 8)
    assert result == '    -999.000,    -999.000'
    assert logged_warnings == ['Infinity encountered in MINIMUM_PHASE_ANGLE',
                               'Infinity encountered in MAXIMUM_PHASE_ANGLE']


def test_out_of_valid_range_becomes_null(make_column: Callable[..., Any]) -> None:
    """Values beyond the template's valid range are replaced by the null value."""
    col = make_column(flag='DEG', valid_minimum=0., valid_maximum=180.)
    # 10 rad -> ~573 deg, outside the valid maximum -> null substitution.
    result = formatting.formatted_column(
        oops.Scalar(np.array([10.0, 10.0]), False), col.stubs, 8)
    assert result == '-999.000,-999.000'


def test_absent_valid_range_skips_the_check(make_column: Callable[..., Any]) -> None:
    """A template declaring no range asks for no range check.

    Under the old format dictionary this was spelled valid_minimum ==
    valid_maximum; a template expresses it by omitting both keywords.
    """
    col = make_column(flag='DEG', valid_minimum=None, valid_maximum=None)
    result = formatting.formatted_column(
        oops.Scalar(np.array([10.0, 10.0]), False), col.stubs, 8)
    assert result == ' 572.958, 572.958'


#===============================================================================
# circle_coverage
#===============================================================================
def test_circle_coverage_masked_scalar_is_double_null() -> None:
    """A fully masked Scalar yields a null pair."""
    assert formatting.circle_coverage(oops.Scalar([1., 2.], True), -999., 8) == \
        [-999., -999.]


def test_circle_coverage_unmasked_passes_through_range() -> None:
    """Dense even sampling reports full [0, 360] coverage."""
    # Dense even sampling -> full coverage [0, 360].
    angles = np.arange(0., 360., 3.0)
    assert formatting.circle_coverage(angles, -999., 8) == [0., 360.]


def test_circle_coverage_minus_180_flag() -> None:
    """The '-180' flag reports coverage in the (-180, 180) convention."""
    # With the smoothing width sampling+1, the four clustered angles smear into
    # apparent full coverage, reported in the (-180, 180) convention.
    result = formatting.circle_coverage(
        oops.Scalar(np.array([350., 355., 5., 10.]), False), -999., 8, flag='-180')
    assert result == [-180., 180.]


def test_circle_coverage_partially_masked_scalar() -> None:
    """Masked angles are ignored; the unmasked ones drive the coverage."""
    # antimask selects the two unmasked angles; the helper still runs.
    scalar = oops.Scalar(np.array([10., 20., 200., 210.]),
                         np.array([False, False, True, True]))
    assert formatting.circle_coverage(scalar, -999., 8) == [0., 360.]


def test_overflow_that_cannot_fit_even_clipped_raises(
        make_column: Callable[..., Any], logged_warnings: list[str]) -> None:
    """A field too narrow for even the clipped overflow value is an error."""
    col = make_column(flag='', overflow='%10.4e', width=5, print_format='%5.1f')
    with pytest.raises(RuntimeError, match=r'column overflow: 1\.0000e\+120'):
        formatting.formatted_column(
            oops.Scalar(np.array([1e120, 1e120]), False), col.stubs, 8)
    assert logged_warnings == []


def test_overflow_clips_and_warns(
        make_column: Callable[..., Any], logged_warnings: list[str]) -> None:
    """Values too wide for the field are logged and clipped to the overflow format."""
    col = make_column(flag='', overflow='%10.4e', width=10, print_format='%10.5f')
    result = formatting.formatted_column(
        oops.Scalar(np.array([1e120, 1e120]), False), col.stubs, 8)
    assert result == '9.9900e+99,9.9900e+99'
    assert logged_warnings == [
        'Column overflow in MINIMUM_PHASE_ANGLE: 1.0000e+120 clipped to 9.9900e+99',
        'Column overflow in MAXIMUM_PHASE_ANGLE: 1.0000e+120 clipped to 9.9900e+99']
