################################################################################
# tests/test_geometry_record.py: Record helpers + bodies_select functions.
################################################################################
"""Tests for Record helpers and the bodies_select functions."""
import types
from collections.abc import Callable
from typing import Any

import oops
import pytest

import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support import bodies_select
from metadata_tools.geometry_support.record import Record


#===============================================================================
# BODYX substitution
#===============================================================================
def test_substitute_binds_bodyx_in_every_key(make_column: Callable[..., Any]) -> None:
    """Record.substitute resolves the BODYX placeholder in each column's key."""
    columns = [make_column(key=('latitude', defs.BODYX, 'centric')),
               make_column(key=('phase_angle', defs.BODYX))]
    bound = Record.substitute(columns, 'IO')

    assert [c.key for c in bound] == [('latitude', 'IO', 'centric'),
                                      ('phase_angle', 'IO')]
    # The originals are untouched, so one body's binding cannot leak into another.
    assert [c.key for c in columns] == [('latitude', defs.BODYX, 'centric'),
                                        ('phase_angle', defs.BODYX)]
    # Stubs ride along unchanged; only the key is rebound.
    assert bound[0].stubs == columns[0].stubs


def test_substitute_resolves_embedded_dict_reference(
        make_column: Callable[..., Any]) -> None:
    """A key holding a dictionary reference resolves once the body is known.

    The ring diameter column's key carries a RING_SYSTEM_RADII lookup keyed by
    the placeholder. util.replace resolves such a reference only inside a nested
    list or tuple leaf, which is why substitute wraps the key before replacing.
    """
    key = ('body_diameter_in_pixels', defs.BODYX + ':RING',
           'defs.RING_SYSTEM_RADII["bodyx"]')
    bound = Record.substitute([make_column(key=key)], 'JUPITER')
    assert bound[0].key[2] == defs.RING_SYSTEM_RADII['JUPITER']


#===============================================================================
# postprocess / link_null
#===============================================================================
def _linked_columns(make_column: Callable[..., Any]) -> list[Any]:
    """Return the two single-valued, null-linked center-coordinate columns."""
    return [make_column(key=('center_coordinate', 'IO', 'u'),
                        names=['CENTER_X_COORDINATE'], flag='', overflow='%12.5e',
                        link_fn='null', link_id='LINK-CENTER_COORDINATE',
                        width=12, print_format='%12.3f', null_value=-99999.),
            make_column(key=('center_coordinate', 'IO', 'v'),
                        names=['CENTER_Y_COORDINATE'], flag='', overflow='%12.5e',
                        link_fn='null', link_id='LINK-CENTER_COORDINATE',
                        width=12, print_format='%12.3f', null_value=-99999.)]


def test_postprocess_propagates_null_across_linked_columns(
        record_stub: Callable[..., Any], make_column: Callable[..., Any]) -> None:
    """A null in one linked column propagates null to its partners."""
    record = record_stub()
    # The first linked column is null (-99999); both must end up null.
    columns = ['"vol"', '"file"', '  -99999.000', '      5.000']
    result = record.postprocess(columns, _linked_columns(make_column))
    assert result[-2:] == ['  -99999.000', '  -99999.000']


def test_postprocess_leaves_non_null_linked_columns(
        record_stub: Callable[..., Any], make_column: Callable[..., Any]) -> None:
    """Linked columns with no null values are left unchanged."""
    record = record_stub()
    columns = ['"vol"', '"file"', '      3.000', '      5.000']
    result = record.postprocess(columns, _linked_columns(make_column))
    assert result[-2:] == ['      3.000', '      5.000']


def test_postprocess_indexes_by_column_not_by_value(
        record_stub: Callable[..., Any], make_column: Callable[..., Any]) -> None:
    """Link positions count columns, not values.

    prep_row appends one string per column, with a min/max column's two values
    already comma-joined inside it. Counting values instead overstates the data
    width, which walks the link positions off the end of the row. It takes
    several two-valued columns ahead of the linked pair for the overcount to
    exceed the row length, which is why the real body table hit this and a
    two-column test did not.
    """
    record = record_stub()
    pair_values = ['  28.648,  57.296', '   1.000,   2.000', '   3.000,   4.000']
    columns = ['"vol"', '"file"', *pair_values, '  -99999.000', '      5.000']
    resolved = [make_column(), make_column(), make_column()] + _linked_columns(make_column)

    result = record.postprocess(columns, resolved)

    assert result == ['"vol"', '"file"', *pair_values,
                      '  -99999.000', '  -99999.000']


def test_postprocess_ignores_unlinked_columns(
        record_stub: Callable[..., Any], make_column: Callable[..., Any]) -> None:
    """Columns with no link id are left alone even when one holds a null."""
    record = record_stub()
    columns = ['"vol"', '"file"', '-999.000', '   5.000']
    unlinked = [make_column(names=['A']), make_column(names=['B'])]
    assert record.postprocess(list(columns), unlinked)[-2:] == ['-999.000', '   5.000']


#===============================================================================
# bodies_select.get_system
#===============================================================================
def _fake_registry(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, str]) -> None:
    """Install a fake oops.Body.BODY_REGISTRY of name -> object(parent.name).

    Parameters:
        monkeypatch: The pytest monkeypatch fixture.
        mapping: Body name to parent body name.
    """
    registry = {}
    for name, parent in mapping.items():
        registry[name] = types.SimpleNamespace(
            parent=types.SimpleNamespace(name=parent))
    monkeypatch.setattr(oops.Body, 'BODY_REGISTRY', registry)


def test_get_system_returns_parent_for_satellite(monkeypatch: pytest.MonkeyPatch) -> None:
    """A satellite's system is its parent planet."""
    _fake_registry(monkeypatch, {'IO': 'JUPITER', 'JUPITER': 'SUN'})
    assert bodies_select.get_system('IO') == 'JUPITER'


def test_get_system_returns_self_for_planet(monkeypatch: pytest.MonkeyPatch) -> None:
    """A planet (child of SUN) is its own system."""
    _fake_registry(monkeypatch, {'JUPITER': 'SUN'})
    assert bodies_select.get_system('JUPITER') == 'JUPITER'


def test_get_system_unknown_body_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unregistered body has no system."""
    _fake_registry(monkeypatch, {})
    assert bodies_select.get_system('NOPE') is None


def test_get_system_root_body_is_self(monkeypatch: pytest.MonkeyPatch) -> None:
    """A root body with no parent, such as the Sun, is its own system."""
    registry = {'SUN': types.SimpleNamespace(parent=None)}
    monkeypatch.setattr(oops.Body, 'BODY_REGISTRY', registry)
    assert bodies_select.get_system('SUN') == 'SUN'


#===============================================================================
# bodies_select.obs_excluded
#===============================================================================
def test_obs_excluded_empty_is_false() -> None:
    """An empty exception list excludes nothing."""
    # `record` is a SimpleNamespace stub standing in for a Record.
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(record, []) is False  # type: ignore[arg-type]


def test_obs_excluded_regex_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """A regex exception matching the observation ID excludes the observation."""
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123CAL')
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(record, ['.*CAL']) is True  # type: ignore[arg-type]


def test_obs_excluded_identifier_calls_config_function(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """An identifier exception calls the named geometry-config function."""
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123')
    config = get_geometry_config()
    monkeypatch.setattr(config, 'always_true_fn', lambda obs: True, raising=False)
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(
        record, ['always_true_fn']) is True  # type: ignore[arg-type]


def test_obs_excluded_identifier_then_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    """The observation is excluded if any exception matches, identifier or regex."""
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123CAL')
    config = get_geometry_config()
    monkeypatch.setattr(config, 'always_false_fn', lambda obs: False, raising=False)
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(
        record, ['always_false_fn', '.*CAL']) is True  # type: ignore[arg-type]


def test_obs_excluded_no_exception_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no matching exception, the observation is not excluded."""
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123')
    config = get_geometry_config()
    monkeypatch.setattr(config, 'always_false_fn', lambda obs: False, raising=False)
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(
        record, ['always_false_fn', '.*CAL']) is False  # type: ignore[arg-type]


#===============================================================================
# bodies_select.get_primary
#===============================================================================
def test_get_primary_in_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """An SCLK inside a row's range returns that row's primary and body lists."""
    monkeypatch.setattr(util, 'sclk_to_ticks', lambda sclk, sc: 150)
    table: list[Any] = [((100, 200), [], 'JUPITER', ['IO'], ['EUROPA'], ['ADRASTEA'])]
    record = types.SimpleNamespace(observation=object())
    # `record` is a SimpleNamespace stub standing in for a Record.
    result = bodies_select.get_primary(record, table, '150')  # type: ignore[arg-type]
    assert result == ('JUPITER', ['IO'], ['EUROPA'], ['ADRASTEA'])


def test_get_primary_no_match_returns_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """An SCLK outside every range returns the empty-primary failure tuple."""
    monkeypatch.setattr(util, 'sclk_to_ticks', lambda sclk, sc: 999)
    table: list[Any] = [((100, 200), [], 'JUPITER', ['IO'], [], [])]
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.get_primary(
        record, table, '999') == ('', [], [], [])  # type: ignore[arg-type]


def test_get_primary_excluded_observation_short_circuits(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A row whose exceptions exclude the observation returns the failure tuple."""
    monkeypatch.setattr(util, 'sclk_to_ticks', lambda sclk, sc: 150)
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0CAL')
    table: list[Any] = [((100, 200), ['.*CAL'], 'JUPITER', ['IO'], [], [])]
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.get_primary(
        record, table, '150') == ('', [], [], [])  # type: ignore[arg-type]
