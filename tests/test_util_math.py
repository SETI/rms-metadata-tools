################################################################################
# tests/test_util_math.py: Pure numeric helpers in util.py.
################################################################################
import numpy as np

import metadata_tools.util as util


#===============================================================================
# add_by_base
#===============================================================================
def test_add_by_base_no_carry():
    assert util.add_by_base([1, 2], [3, 4], [10, 10]) == [0, 4, 6]


def test_add_by_base_single_carry():
    # 5 + 5 == 10 -> carry into the next position.
    assert util.add_by_base([5], [5], [10]) == [1, 0]


def test_add_by_base_sclk_bases():
    bases = [16777215, 91, 10, 8]
    assert util.add_by_base([0, 0, 0, 0], [0, 0, 0, 1], bases) == [0, 0, 0, 0, 1]


def test_add_by_base_propagates_chained_carry():
    # 99 + 01 == 100. The carry must propagate through the middle position.
    assert util.add_by_base([9, 9], [0, 1], [10, 10]) == [1, 0, 0]


#===============================================================================
# rebase
#===============================================================================
def test_rebase_exact():
    assert util.rebase(123, [10, 10, 10]) == ([1, 2, 3], 0)


def test_rebase_overflow_returns_remainder():
    digits, over = util.rebase(1234, [10, 10, 10])
    assert digits == [2, 3, 4]
    assert over == 1


def test_rebase_ceil_rounds_fraction_up():
    # ceil rounds the fractional tick of the last place up.
    digits, _ = util.rebase(10.5, [10, 10], ceil=True)
    assert digits[-1] == 1


def test_add_by_base_then_rebase_roundtrip():
    bases = [10, 10, 10]
    digits, over = util.rebase(457, bases)
    assert over == 0
    # Adding zero must leave the digit representation unchanged.
    assert util.add_by_base(digits, [0, 0, 0], bases) == [0, *digits]


#===============================================================================
# sclk_split_count / sclk_format_count
#===============================================================================
def test_sclk_split_count_explicit_delim():
    assert util.sclk_split_count('12345:01:2:3') == [12345, 1, 2, 3]


def test_sclk_split_count_pads_to_four_fields():
    assert util.sclk_split_count('100.2.3') == [100, 2, 3, 0]


def test_sclk_split_count_default_delim_any_nonalnum():
    # With delim=None, every non-alphanumeric is treated as a delimiter.
    assert util.sclk_split_count('100-2-3') == [100, 2, 3, 0]


def test_sclk_format_count_zero_pads():
    result = util.sclk_format_count([12345, 1, 2, 3], 'nnnnnnnn:nn:n.n')
    assert result == '00012345:01:2.3'


def test_sclk_format_count_returns_str_not_int():
    # The docstring claims `Returns: int`, but a delimited string is returned.
    result = util.sclk_format_count([12345, 1, 2, 3], 'nnnnnnnn:nn:n.n')
    assert isinstance(result, str)


def test_sclk_split_format_roundtrip():
    fmt = 'nnnnnnnn:nn:n:n'
    counts = util.sclk_split_count('00012345:01:2:3')
    assert util.sclk_format_count(counts, fmt) == '00012345:01:2:3'


#===============================================================================
# convert_mission_table
#===============================================================================
def test_convert_mission_table_drops_label_and_converts_ticks(monkeypatch):
    monkeypatch.setattr(util, 'sclk_to_ticks', lambda sclk, sc: int(sclk))
    # Source row: (phase_label, (sclk0, sclk1), exceptions, primary,
    #              secondaries, selections, additions).
    table = [('PHASE_LABEL', ('100', '200'), ['BAD_OBS'], 'JUPITER',
              ['IO'], ['EUROPA'], ['ADRASTEA'])]
    converted = util.convert_mission_table(table, -77)
    # The phase label (item[0]) is dropped; the SCLK pair becomes ticks.
    assert converted == [((100, 200), ['BAD_OBS'], 'JUPITER',
                          ['IO'], ['EUROPA'], ['ADRASTEA'])]


#===============================================================================
# pm / smooth
#===============================================================================
def test_pm_returns_plus_minus():
    assert list(util.pm(3)) == [3, -3]


def test_smooth_moving_box():
    result = util.smooth(np.array([1., 2., 3., 4.]), 2)
    np.testing.assert_allclose(result, [0.5, 1.5, 2.5, 3.5])


#===============================================================================
# range_of_n_angles (statistical helper; exercised for coverage)
#===============================================================================
def test_range_of_n_angles_is_bounded():
    result = util.range_of_n_angles(5, tests=200)
    assert 0.0 <= result <= 360.0


#===============================================================================
# dbprint (debug helper; exercised for coverage)
#===============================================================================
def test_dbprint_writes_to_stderr(capsys):
    util.dbprint('hello-debug')
    captured = capsys.readouterr()
    assert 'hello-debug' in captured.err
