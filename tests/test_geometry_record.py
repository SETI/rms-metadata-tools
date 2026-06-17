################################################################################
# tests/test_geometry_record.py: Record helpers + bodies_select functions.
################################################################################
import types
from collections.abc import Callable
from typing import Any

import oops
import pytest

import metadata_tools.util as util
from metadata_tools.geometry_support import bodies_select
from metadata_tools.geometry_support.record import Record


#===============================================================================
# get_backplane_key
#===============================================================================
def test_get_backplane_key_tuple_event_key() -> None:
    desc = (('phase_angle', 'IO'), ('', '', ''))
    assert Record.get_backplane_key(desc) == 'phase_angle'


def test_get_backplane_key_plain_event_key() -> None:
    # The docstring claims `Returns: None`; it actually returns the key.
    desc = ('phase_angle', ('', '', ''))
    assert Record.get_backplane_key(desc) == 'phase_angle'


#===============================================================================
# get_key_map
#===============================================================================
def test_get_key_map_slices_last_ndata_columns(
        record_stub: Callable[..., Any]) -> None:
    record = record_stub(backplane_keys={}, dicts={
        'body': [(('center_coordinate', 'IO', 'u'), ('', '', '')),
                 (('center_coordinate', 'IO', 'v'), ('', '', ''))]})
    columns = ['"vol"', '"file"', ' a', ' b']
    keys, data = record.get_key_map(columns, 'body')
    assert keys == ['center_coordinate', 'center_coordinate']
    assert data == [' a', ' b']


def test_get_key_map_caches_per_qualifier(record_stub: Callable[..., Any]) -> None:
    record = record_stub(backplane_keys={}, dicts={
        'sky': [(('right_ascension', 'SKY'), ('', '', ''))]})
    record.get_key_map(['"v"', 'x'], 'sky')
    assert record.backplane_keys['sky'] == ['right_ascension']
    # Second call uses the cached value (mutating dicts must not matter now).
    record.dicts['sky'] = 'ignored'
    keys, _ = record.get_key_map(['"v"', 'y'], 'sky')
    assert keys == ['right_ascension']


def test_get_key_map_handles_dict_of_named_lists(record_stub: Callable[..., Any]) -> None:
    record = record_stub(backplane_keys={}, dicts={
        'ring': {'SATURN': [(('ring_radius', 'SATURN'), ('', '', ''))]}})
    keys, _ = record.get_key_map(['"v"', 'r'], 'ring')
    assert keys == ['ring_radius']


#===============================================================================
# postprocess / link_null
#===============================================================================
def test_postprocess_propagates_null_across_linked_columns(
        record_stub: Callable[..., Any]) -> None:
    record = record_stub(backplane_keys={}, dicts={
        'body': [(('center_coordinate', 'IO', 'u'), ('', '', '')),
                 (('center_coordinate', 'IO', 'v'), ('', '', ''))]})
    # The first linked column is null (-99999); both must end up null.
    columns = ['"vol"', '"file"', '  -99999.000', '      5.000']
    result = record.postprocess(columns, 'body')
    assert result[-2:] == ['  -99999.000', '  -99999.000']


def test_postprocess_leaves_non_null_linked_columns(
        record_stub: Callable[..., Any]) -> None:
    record = record_stub(backplane_keys={}, dicts={
        'body': [(('center_coordinate', 'IO', 'u'), ('', '', '')),
                 (('center_coordinate', 'IO', 'v'), ('', '', ''))]})
    columns = ['"vol"', '"file"', '      3.000', '      5.000']
    result = record.postprocess(columns, 'body')
    assert result[-2:] == ['      3.000', '      5.000']


#===============================================================================
# bodies_select.get_system
#===============================================================================
def _fake_registry(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, str]) -> None:
    """Install a fake oops.Body.BODY_REGISTRY of name -> object(parent.name)."""
    registry = {}
    for name, parent in mapping.items():
        registry[name] = types.SimpleNamespace(
            parent=types.SimpleNamespace(name=parent))
    monkeypatch.setattr(oops.Body, 'BODY_REGISTRY', registry)


def test_get_system_returns_parent_for_satellite(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_registry(monkeypatch, {'IO': 'JUPITER', 'JUPITER': 'SUN'})
    assert bodies_select.get_system('IO') == 'JUPITER'


def test_get_system_returns_self_for_planet(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_registry(monkeypatch, {'JUPITER': 'SUN'})
    assert bodies_select.get_system('JUPITER') == 'JUPITER'


def test_get_system_unknown_body_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_registry(monkeypatch, {})
    assert bodies_select.get_system('NOPE') is None


#===============================================================================
# bodies_select.obs_excluded
#===============================================================================
def test_obs_excluded_empty_is_false() -> None:
    # `record` is a SimpleNamespace stub standing in for a Record.
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(record, []) is False  # type: ignore[arg-type]


def test_obs_excluded_regex_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123CAL')
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(record, ['.*CAL']) is True  # type: ignore[arg-type]


def test_obs_excluded_identifier_calls_config_function(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123')
    import geometry_config as config
    monkeypatch.setattr(config, 'always_true_fn', lambda obs: True, raising=False)
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(
        record, ['always_true_fn']) is True  # type: ignore[arg-type]


def test_obs_excluded_identifier_then_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123CAL')
    import geometry_config as config
    monkeypatch.setattr(config, 'always_false_fn', lambda obs: False, raising=False)
    record = types.SimpleNamespace(observation=object())
    # The first (identifier) exception does not match, but a later regex does;
    # the observation is excluded if *any* exception matches.
    assert bodies_select.obs_excluded(
        record, ['always_false_fn', '.*CAL']) is True  # type: ignore[arg-type]


def test_obs_excluded_no_exception_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0123')
    import geometry_config as config
    monkeypatch.setattr(config, 'always_false_fn', lambda obs: False, raising=False)
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.obs_excluded(
        record, ['always_false_fn', '.*CAL']) is False  # type: ignore[arg-type]


#===============================================================================
# bodies_select.get_primary
#===============================================================================
def test_get_primary_in_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(util, 'sclk_to_ticks', lambda sclk, sc: 150)
    table: list[Any] = [((100, 200), [], 'JUPITER', ['IO'], ['EUROPA'], ['ADRASTEA'])]
    record = types.SimpleNamespace(observation=object())
    # `record` is a SimpleNamespace stub standing in for a Record.
    result = bodies_select.get_primary(record, table, '150')  # type: ignore[arg-type]
    assert result == ('JUPITER', ['IO'], ['EUROPA'], ['ADRASTEA'])


def test_get_primary_no_match_returns_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(util, 'sclk_to_ticks', lambda sclk, sc: 999)
    table: list[Any] = [((100, 200), [], 'JUPITER', ['IO'], [], [])]
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.get_primary(
        record, table, '999') == ('', [], [], [])  # type: ignore[arg-type]


def test_get_primary_excluded_observation_short_circuits(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(util, 'sclk_to_ticks', lambda sclk, sc: 150)
    monkeypatch.setattr(util, 'get_observation_id', lambda obs: 'C0CAL')
    table: list[Any] = [((100, 200), ['.*CAL'], 'JUPITER', ['IO'], [], [])]
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.get_primary(
        record, table, '150') == ('', [], [], [])  # type: ignore[arg-type]
