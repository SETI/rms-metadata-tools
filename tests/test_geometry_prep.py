################################################################################
# tests/test_geometry_prep.py: prep_row + append_body_prefix (fake Backplane).
################################################################################
import numpy as np
import oops
import pytest

from metadata_tools.geometry_support import prep


@pytest.fixture
def exists_true(monkeypatch):
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))


def _record(record_stub, pointing=True, sampling=8):
    return record_stub(pointing_available=pointing, sampling=sampling)


def _phase_desc():
    return [(('phase_angle', 'IO'), ('', '', ''))]


#===============================================================================
# append_body_prefix
#===============================================================================
def test_append_body_prefix_pads_short_name():
    cols = []
    prep.append_body_prefix(cols, 'IO', 12)
    assert cols == ['"IO          "']


def test_append_body_prefix_none_is_blank_field():
    cols = []
    prep.append_body_prefix(cols, None, 12)
    assert cols == ['"            "']


def test_append_body_prefix_truncates_long_name():
    cols = []
    prep.append_body_prefix(cols, 'ABCDEFGHIJKLMNOP', 12)
    assert cols == ['"ABCDEFGHIJKL"']


#===============================================================================
# prep_row summary path
#===============================================================================
def test_summary_writes_single_row(record_stub, fake_backplane):
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    rows, overrides = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_desc(), primary='JUPITER', target='IO', no_mask=True)
    assert len(rows) == 1
    assert rows[0][-1] == '  28.648,  57.296'
    assert len(overrides) == 1


def test_summary_no_body_omits_prefixes(record_stub, fake_backplane):
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    rows, _ = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_desc(), primary='JUPITER', target='IO', no_mask=True, no_body=True)
    # Only the two prefixes + one data column, no body-name columns inserted.
    assert len(rows[0]) == 3


def test_primary_prefix_when_no_target(record_stub, fake_backplane):
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    rows, _ = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_desc(), primary='JUPITER', target=None, no_mask=True)
    assert rows[0][2] == '"JUPITER     "'


def test_pointing_unavailable_writes_null_row(record_stub, fake_backplane):
    rows, _ = prep.prep_row(
        _record(record_stub, pointing=False), ['"vol"', '"file"'],
        fake_backplane, None, _phase_desc(), primary='JUPITER', target='IO',
        no_mask=True, allow_zero_rows=False)
    # null_flag path substitutes the null value (-999) for every column; with
    # allow_zero_rows=False a null row is forced rather than suppressed.
    assert rows[0][-1] == '-999.000,-999.000'


def test_excluded_mask_applied_when_not_no_mask(exists_true, record_stub, fake_backplane):
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.full((4, 4), 0.5), False)
    # Mask out everything -> the only row is suppressed unless allow_zero_rows.
    fake_backplane.in_back[('IO', 'JUPITER')] = np.ones((4, 4), dtype=bool)
    descs = [(('phase_angle', 'IO'), ('P', '', ''))]
    rows, _ = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        descs, primary='JUPITER', target='IO', allow_zero_rows=True)
    # Fully excluded + allow_zero_rows -> nothing_found suppresses the row.
    assert rows == []


def test_override_is_built_per_column(record_stub, fake_backplane):
    # Each row's overrides hold one dict per column, in column order.
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    fake_backplane.evaluations[('distance', 'IO')] = \
        oops.Scalar(np.array([100., 200.]), False)
    descs = [(('phase_angle', 'IO'), ('', '', '')),
             (('distance', 'IO'), ('', '', ''))]
    _rows, overrides = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        descs, primary='JUPITER', target='IO', no_mask=True)
    # overrides[row][column]; phase_angle keeps VALID_MAXIMUM 180, distance 0.
    assert overrides[0][0]['VALID_MAXIMUM'] == 180
    assert overrides[0][1]['VALID_MAXIMUM'] == 0


#===============================================================================
# prep_row detailed (tiled) path
#===============================================================================
def test_tiling_suppressed_below_min(record_stub, fake_backplane):
    # global area smaller than tiling_min -> tiles cleared -> summary row.
    small = np.zeros((4, 4), dtype=bool)
    small[0, 0] = True
    fake_backplane.evaluations['global'] = oops.Scalar(small, False)
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.array([0.5, 1.0]), False)
    rows, _ = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_desc(), primary='JUPITER', target='IO', tiles=['global', 't1'],
        tiling_min=100, no_mask=True)
    # Collapsed to a single summary row (no subregion index column present is
    # not asserted here; just that exactly one row is produced).
    assert len(rows) == 1


def test_multiple_tile_sets_tuple_emits_a_row_per_set(record_stub, fake_backplane):
    # When `tiles` is a tuple (multiple tile sets), prep_row recurses once per
    # set; the recursion now passes the keyword-only arguments by keyword, so it
    # no longer raises TypeError.
    big = np.ones((4, 4), dtype=bool)
    t1 = np.zeros((4, 4), dtype=bool)
    t1[0, :] = True
    t2 = np.zeros((4, 4), dtype=bool)
    t2[1, :] = True
    fake_backplane.evaluations['global'] = oops.Scalar(big, False)
    fake_backplane.evaluations['t1'] = oops.Scalar(t1, False)
    fake_backplane.evaluations['t2'] = oops.Scalar(t2, False)
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.full((4, 4), 0.5), False)
    rows, _ = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_desc(), primary='JUPITER', target='IO',
        tiles=(['global', 't1'], ['global', 't2']), tiling_min=1, no_mask=True)
    # One non-empty subregion per tile set -> two rows.
    assert len(rows) == 2


def test_detailed_subregions_emit_rows(record_stub, fake_backplane):
    big = np.ones((4, 4), dtype=bool)
    tile1 = np.zeros((4, 4), dtype=bool)
    tile1[0, :] = True
    fake_backplane.evaluations['global'] = oops.Scalar(big, False)
    fake_backplane.evaluations['t1'] = oops.Scalar(tile1, False)
    fake_backplane.evaluations[('phase_angle', 'IO')] = \
        oops.Scalar(np.full((4, 4), 0.5), False)
    rows, _ = prep.prep_row(
        _record(record_stub), ['"vol"', '"file"'], fake_backplane, None,
        _phase_desc(), primary='JUPITER', target='IO', tiles=['global', 't1'],
        tiling_min=1, no_mask=True)
    assert len(rows) == 1
    # A subregion index column was inserted before the data column.
    assert rows[0][-2].strip().isdigit()
