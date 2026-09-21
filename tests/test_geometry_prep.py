################################################################################
# tests/test_geometry_prep.py: prep_row + append_body_prefix (fake Backplane).
################################################################################
"""Tests for prep_row and append_body_prefix using the conftest FakeBackplane."""
from collections.abc import Callable
from typing import Any

import numpy as np
import oops

from metadata_tools.geometry_support import prep
from metadata_tools.geometry_support.record import Record


def _record(record_stub: Callable[..., Record], pointing: bool = True,
            sampling: int = 8) -> Record:
    """Build a bare Record stub carrying the attributes prep_row reads.

    Parameters:
        record_stub: The conftest record_stub factory fixture.
        pointing: Value for the pointing_available attribute.
        sampling: Value for the sampling attribute.

    Returns:
        The attribute-only Record stub.
    """
    return record_stub(pointing_available=pointing, sampling=sampling)


def _phase_cols(make_column: Callable[..., Any],
                mask: tuple[str, str, str] = ('', '', '')) -> list[Any]:
    """Return a one-column schema: the IO phase-angle min/max pair."""
    return [make_column(key=('phase_angle', 'IO'), mask=mask, flag='DEG',
                        valid_minimum=0., valid_maximum=180.)]


#===============================================================================
# append_body_prefix
#===============================================================================
def test_append_body_prefix_pads_short_name() -> None:
    """A short body name is right-padded to the field width."""
    cols: list[str] = []
    prep.append_body_prefix(cols, 'IO', 12)
    assert cols == ['"IO          "']


def test_append_body_prefix_none_is_blank_field() -> None:
    """A None body yields an all-blank quoted field."""
    cols: list[str] = []
    prep.append_body_prefix(cols, None, 12)
    assert cols == ['"            "']


def test_append_body_prefix_truncates_long_name() -> None:
    """A long body name is truncated to the field width."""
    cols: list[str] = []
    prep.append_body_prefix(cols, 'ABCDEFGHIJKLMNOP', 12)
    assert cols == ['"ABCDEFGHIJKL"']


#===============================================================================
# prep_row summary path
#===============================================================================
def test_summary_writes_single_row(
        record_stub: Callable[..., Record], fake_backplane: Any,
        make_column: Callable[..., Any]) -> None:
    """The summary path emits one formatted row."""
    # fake_backplane: conftest-private FakeBackplane stand-in for oops.Backplane.
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    rows = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_cols(make_column), primary='JUPITER', target='IO', no_mask=True)
    assert len(rows) == 1
    assert rows[0][-1] == '  28.648,  57.296'


def test_summary_no_body_omits_prefixes(
        record_stub: Callable[..., Record], fake_backplane: Any,
        make_column: Callable[..., Any]) -> None:
    """With no_body=True no body-name columns are inserted."""
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    rows = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_cols(make_column), primary='JUPITER', target='IO', no_mask=True, no_body=True)
    # Only the two prefixes + one data column, no body-name columns inserted.
    assert len(rows[0]) == 3


def test_primary_prefix_when_no_target(
        record_stub: Callable[..., Record], fake_backplane: Any,
        make_column: Callable[..., Any]) -> None:
    """With no target, the primary name fills the body prefix column."""
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    rows = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_cols(make_column), primary='JUPITER', target=None, no_mask=True)
    assert rows[0][2] == '"JUPITER     "'


def test_pointing_unavailable_writes_null_row(
        record_stub: Callable[..., Record], fake_backplane: Any,
        make_column: Callable[..., Any]) -> None:
    """Without pointing, a forced null row is written if allow_zero_rows is False."""
    rows = prep.prep_row(
        _record(record_stub, pointing=False), ['"vol"', '"file"'],
        fake_backplane, None, _phase_cols(make_column), primary='JUPITER', target='IO',
        no_mask=True, allow_zero_rows=False)
    # null_flag path substitutes the null value (-999) for every column; with
    # allow_zero_rows=False a null row is forced rather than suppressed.
    assert rows[0][-1] == '-999.000,-999.000'


def test_excluded_mask_applied_when_not_no_mask(
        exists_true: None, record_stub: Callable[..., Record],
        fake_backplane: Any,
        make_column: Callable[..., Any]) -> None:
    """A fully excluded mask suppresses the row when allow_zero_rows is True."""
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.full((4, 4), 0.5), False)
    # Mask out everything -> the only row is suppressed unless allow_zero_rows.
    fake_backplane.in_back[('IO', 'JUPITER')] = np.ones((4, 4), dtype=bool)
    rows = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_cols(make_column, mask=('P', '', '')), primary='JUPITER',
        target='IO', allow_zero_rows=True)
    # Fully excluded + allow_zero_rows -> nothing_found suppresses the row.
    assert rows == []
