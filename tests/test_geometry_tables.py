################################################################################
# tests/test_geometry_tables.py: table classes, Record.add, Suite helpers.
################################################################################
"""Tests for the geometry table classes, Record.add, and Suite helpers."""
import types
from collections.abc import Callable
from typing import Any

import numpy as np
import oops
import pytest

import metadata_tools.common as com
from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support import suite as suite_mod
from metadata_tools.geometry_support import tables
from metadata_tools.geometry_support.record import Record
from metadata_tools.geometry_support.suite import Suite

config = get_geometry_config()


class RecordingRecord:
    """A stand-in record whose .add records the dispatch arguments."""

    def __init__(self, **attrs: Any) -> None:
        """Store attributes and start an empty call log."""
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.__dict__.update(attrs)

    def add(self, qualifier: str, **kwargs: Any) -> list[str]:
        """Record the dispatch arguments and return a synthetic row."""
        self.calls.append((qualifier, kwargs))
        return [f'row:{qualifier}:{kwargs}']


#===============================================================================
# Table.add dispatch
#===============================================================================
def test_inventory_table_add_formats_prefixes_and_list() -> None:
    """InventoryTable.add joins the prefixes and body list into one CSV row."""
    table = tables.InventoryTable()
    record = types.SimpleNamespace(prefixes=['"vol"', '"file"'],
                                   inventory=['IO', 'EUROPA'])
    table.add(record)  # type: ignore[arg-type]
    assert table.rows == ['"vol","file","IO,EUROPA"']


def test_sky_table_add_uses_no_body() -> None:
    """SkyTable.add dispatches with no_body=True."""
    table = tables.SkyTable(level='summary')
    record = RecordingRecord()
    table.add(record)  # type: ignore[arg-type]
    assert record.calls == [('sky', {'no_body': True})]


def test_sun_table_add_targets_sun() -> None:
    """SunTable.add dispatches with the fixed target SUN (body-style prefix)."""
    table = tables.SunTable(level='summary')
    record = RecordingRecord()
    table.add(record)  # type: ignore[arg-type]
    assert record.calls == [('sun', {'target': 'SUN'})]


def test_ring_table_add_only_when_rings_present() -> None:
    """RingTable.add dispatches with the primary's name when rings are present."""
    table = tables.RingTable(level='summary')
    record = RecordingRecord(primary='JUPITER', rings_present=True)
    table.add(record)  # type: ignore[arg-type]
    assert record.calls == [('ring', {'name': 'JUPITER'})]


def test_ring_table_add_skips_without_rings() -> None:
    """RingTable.add skips records without rings."""
    table = tables.RingTable(level='summary')
    record = RecordingRecord(primary='JUPITER', rings_present=False)
    table.add(record)  # type: ignore[arg-type]
    assert record.calls == []


def test_ring_table_add_skips_without_primary() -> None:
    """RingTable.add skips records without a primary."""
    table = tables.RingTable(level='summary')
    record = RecordingRecord(primary='', rings_present=True)
    table.add(record)  # type: ignore[arg-type]
    assert record.calls == []


def test_body_table_add_iterates_bodies() -> None:
    """BodyTable.add dispatches once per body with matching name and target."""
    table = tables.BodyTable(level='summary')
    record = RecordingRecord(bodies=['IO', 'EUROPA'])
    table.add(record)  # type: ignore[arg-type]
    assert record.calls == [
        ('body', {'name': 'IO', 'target': 'IO'}),
        ('body', {'name': 'EUROPA', 'target': 'EUROPA'})]


#===============================================================================
# Record.add (drives prep_row + postprocess end to end)
#===============================================================================
class _Backplane:
    """A minimal Backplane stub returning fixed Scalars and empty masks."""
    shape = (4, 4)

    def evaluate(self, key: Any) -> Any:
        """Return a fixed two-value Scalar for any key."""
        return oops.Scalar(np.array([0.5, 1.0]), False)

    def where_in_back(self, target: str, obscurer: str) -> Any:
        """Return an all-False where-mask."""
        return types.SimpleNamespace(vals=np.zeros((4, 4), dtype=bool))

    where_inside_shadow = where_in_back

    def where_antisunward(self, target: str) -> Any:
        """Return an all-False where-mask."""
        return types.SimpleNamespace(vals=np.zeros((4, 4), dtype=bool))

    where_sunward = where_antisunward


def test_record_add_builds_summary_line(
        record_stub: Callable[..., Record],
        monkeypatch: pytest.MonkeyPatch) -> None:
    """add('sky') formats prefixes plus the evaluated backplane column."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    record = record_stub(
        pointing_available=True, sampling=8, backplane_keys={}, blocker=None,
        primary='JUPITER', prefixes=['"vol"', '"file"'], backplane=_Backplane(),
        dicts={'sky': [(('phase_angle', 'IO'), ('', '', ''))]})
    lines = record.add('sky', no_body=True)
    assert lines == ['"vol","file",  28.648,  57.296']


def test_record_add_named_column_dict(
        record_stub: Callable[..., Record],
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A named column dict selects the list under the given name."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    record = record_stub(
        pointing_available=True, sampling=8, backplane_keys={}, blocker=None,
        primary='JUPITER', prefixes=['"vol"', '"file"'], backplane=_Backplane(),
        dicts={'ring': {'JUPITER': [(('phase_angle', 'IO'), ('', '', ''))]}})
    lines = record.add('ring', name='JUPITER', no_body=True)
    assert lines[0].endswith('  28.648,  57.296')


#===============================================================================
# Suite static / light helpers
#===============================================================================
def _override_record(record_stub: Callable[..., Record]) -> Record:
    """Return a Record stub with sky/ring/body column dicts for override tests."""
    return record_stub(primary='JUPITER', dicts={
        'sky': [(('right_ascension', 'SKY'), ('', '', ''))],
        'ring': {'JUPITER': [(('ring_radius', 'JUPITER'), ('', '', ''))]},
        'body': {'JUPITER': [(('phase_angle', 'JUPITER'), ('', '', ''))]}})


def test_suite_get_override_builds_one_dict_per_column(
        record_stub: Callable[..., Record]) -> None:
    """get_override builds one NULL/VALID dict per data column."""
    record = _override_record(record_stub)
    overrides = Suite.get_override(record, 'sky')
    assert overrides == [{'NULL_VALUE': -999., 'VALID_MINIMUM': 0,
                          'VALID_MAXIMUM': 360}]


def test_suite_get_override_named(record_stub: Callable[..., Record]) -> None:
    """get_override resolves a named dict entry before building overrides."""
    record = _override_record(record_stub)
    overrides = Suite.get_override(record, 'ring', name='JUPITER')
    assert len(overrides) == 1
    assert overrides[0]['NULL_VALUE'] == -999.


def test_suite_get_overrides_covers_sky_ring_body(
        record_stub: Callable[..., Record]) -> None:
    """get_overrides covers the sky, ring, and body qualifiers (no sun)."""
    record = _override_record(record_stub)
    overrides = Suite.get_overrides(record)
    # No 'sun': the sun table is not wired in (see tables.SunTable).
    assert set(overrides) == {'sky', 'ring', 'body'}


def test_suite_add_tables_creates_four_tables(
        record_stub: Callable[..., Record]) -> None:
    """add_tables registers the inventory, sky, ring, and body tables."""
    suite = Suite.__new__(Suite)
    suite.template_path = None  # type: ignore[assignment]
    suite.volume_id = 'GO_0001'
    suite.add_tables(None, 'summary')  # type: ignore[arg-type]
    qualifiers = [t.qualifier for t in suite.tables]
    # No 'sun': the sun table is not wired in (see tables.SunTable).
    assert qualifiers == ['inventory', 'sky', 'ring', 'body']


def test_suite_make_records_one_per_level(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """make_records builds one Record per configured level."""
    suite = Suite.__new__(Suite)
    suite.observations = ['obs0']
    suite.volume_id = 'GO_0001'
    suite.meshgrids = {}
    suite.sampling = 8
    suite.levels = ['summary', 'detailed']
    created: list[Any] = []
    monkeypatch.setattr(
        suite_mod, 'Record',
        lambda *args: created.append(args[-1]) or args[-1])  # type: ignore[func-returns-value]
    records = suite.make_records(0)
    assert records == ['summary', 'detailed']  # type: ignore[comparison-overlap]


def test_suite_add_dispatches_by_level() -> None:
    """add() routes records to level-matched tables; level-None tables take all."""
    suite = Suite.__new__(Suite)
    sky: Any = types.SimpleNamespace(level='summary', added=[],
                                     add=lambda r: sky.added.append(r))
    inv: Any = types.SimpleNamespace(level=None, added=[],
                                     add=lambda r: inv.added.append(r))
    suite.tables = [sky, inv]
    rec_sum = types.SimpleNamespace(level='summary')
    suite.add([rec_sum])  # type: ignore[list-item]
    assert sky.added == [rec_sum]
    assert inv.added == [rec_sum]  # level None tables take every record


def test_suite_write_calls_each_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """write() forwards labels_only to every table."""
    suite = Suite.__new__(Suite)
    written: list[bool] = []
    suite.tables = [
        types.SimpleNamespace(  # type: ignore[list-item]
            write=lambda labels_only: written.append(labels_only))]
    suite.write(labels_only=True)
    assert written == [True]


def test_suite_create_returns_early_without_observations() -> None:
    """Without an observations attribute, create() returns immediately."""
    suite = Suite.__new__(Suite)
    assert suite.create() is None  # type: ignore[func-returns-value]


def test_suite_create_processes_observations(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """create() makes, adds, and writes records for a matching observation."""
    suite = Suite.__new__(Suite)
    suite.observations = [types.SimpleNamespace(basename='C0123.IMG',
                                                filespec='data/C0123.IMG')]
    suite.glob = 'C0*'
    suite.first = None
    suite.volume_id = 'GO_0001'
    added: list[Any] = []
    written: list[Any] = []
    monkeypatch.setattr(Suite, 'make_records', lambda self, i: ['rec'])
    monkeypatch.setattr(Suite, 'add', lambda self, records: added.append(records))
    monkeypatch.setattr(Suite, 'write',
                        lambda self, labels_only=False: written.append(labels_only))
    monkeypatch.setattr(config, 'cleanup', lambda: None, raising=False)
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda: None))
    suite.create()
    assert added == [['rec']]
    assert written == [False]


def test_suite_create_skips_glob_mismatch(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Observations not matching the glob are skipped entirely."""
    suite = Suite.__new__(Suite)
    suite.observations = [types.SimpleNamespace(basename='OTHER.IMG',
                                                filespec='data/OTHER.IMG')]
    suite.glob = 'C0*'
    suite.first = None
    suite.volume_id = 'GO_0001'
    added: list[Any] = []
    monkeypatch.setattr(Suite, 'make_records', lambda self, i: ['rec'])
    monkeypatch.setattr(Suite, 'add', lambda self, records: added.append(records))
    monkeypatch.setattr(Suite, 'write', lambda self, labels_only=False: None)
    monkeypatch.setattr(config, 'cleanup', lambda: None, raising=False)
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda: None))
    suite.create()
    # The lone observation does not match the glob -> nothing added.
    assert added == []
