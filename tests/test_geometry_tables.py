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
import metadata_tools.defs as defs
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
        self.calls: list[tuple[Any, dict[str, Any]]] = []
        self.__dict__.update(attrs)

    def add(self, columns: Any, **kwargs: Any) -> list[str]:
        """Record the dispatch arguments and return a synthetic row."""
        self.calls.append((columns, kwargs))
        return [f'row:{kwargs}']


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


def _with_schema(table: Any, columns: Any = ('COLS',)) -> Any:
    """Attach a stub schema to a bare table, standing in for a resolved template."""
    table.schema = types.SimpleNamespace(columns=columns)
    return table


def test_sky_table_add_uses_no_body() -> None:
    """SkyTable.add hands its resolved columns over with no_body=True."""
    table = _with_schema(tables.SkyTable(level='summary'))
    record = RecordingRecord()
    table.add(record)
    assert record.calls == [(('COLS',), {'no_body': True})]


def test_sun_table_add_targets_sun() -> None:
    """SunTable.add dispatches with the fixed target SUN (body-style prefix)."""
    table = _with_schema(tables.SunTable(level='summary'))
    record = RecordingRecord()
    table.add(record)
    assert record.calls == [(('COLS',), {'target': 'SUN'})]


def test_ring_table_add_only_when_rings_present() -> None:
    """RingTable.add dispatches with the primary's name when rings are present."""
    table = _with_schema(tables.RingTable(level='summary'))
    record = RecordingRecord(primary='JUPITER', rings_present=True)
    table.add(record)
    assert record.calls == [(('COLS',), {'name': 'JUPITER'})]


def test_ring_table_add_skips_without_rings() -> None:
    """RingTable.add skips records without rings."""
    table = _with_schema(tables.RingTable(level='summary'))
    record = RecordingRecord(primary='JUPITER', rings_present=False)
    table.add(record)
    assert record.calls == []


def test_ring_table_add_skips_without_primary() -> None:
    """RingTable.add skips records without a primary."""
    table = _with_schema(tables.RingTable(level='summary'))
    record = RecordingRecord(primary='', rings_present=True)
    table.add(record)
    assert record.calls == []


def test_body_table_add_iterates_bodies() -> None:
    """BodyTable.add dispatches once per body with matching name and target."""
    table = _with_schema(tables.BodyTable(level='summary'))
    record = RecordingRecord(bodies=['IO', 'EUROPA'])
    table.add(record)
    assert record.calls == [
        (('COLS',), {'name': 'IO', 'target': 'IO'}),
        (('COLS',), {'name': 'EUROPA', 'target': 'EUROPA'})]


#===============================================================================
# Record.add (drives prep_row + postprocess end to end)
#===============================================================================
class _Backplane:
    """A minimal Backplane stub returning fixed Scalars and empty masks."""
    shape = (4, 4)
    # masks.py reads backplane.meshgrid.shape (oops >= 0.3 interface).
    meshgrid = types.SimpleNamespace(shape=(4, 4))

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
        record_stub: Callable[..., Record], make_column: Callable[..., Any],
        monkeypatch: pytest.MonkeyPatch) -> None:
    """add() formats prefixes plus the evaluated backplane column."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    record = record_stub(
        pointing_available=True, sampling=8, blocker=None,
        primary='JUPITER', prefixes=['"vol"', '"file"'], backplane=_Backplane())
    columns = [make_column(key=('phase_angle', 'IO'), flag='DEG',
                           valid_minimum=0., valid_maximum=180.)]
    lines = record.add(columns, no_body=True)
    assert lines == ['"vol","file",  28.648,  57.296']


def test_record_add_binds_the_body_name(
        record_stub: Callable[..., Record], make_column: Callable[..., Any],
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A name binds the BODYX placeholder before the backplane is evaluated."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    seen: list[Any] = []

    class _Recording(_Backplane):
        """A backplane that records the keys it is asked to evaluate."""

        def evaluate(self, key: Any) -> Any:
            """Record the key, then defer to the fixed stub value."""
            seen.append(key)
            return super().evaluate(key)

    record = record_stub(
        pointing_available=True, sampling=8, blocker=None,
        primary='JUPITER', prefixes=['"vol"', '"file"'], backplane=_Recording())
    columns = [make_column(key=('phase_angle', defs.BODYX), flag='DEG',
                           valid_minimum=0., valid_maximum=180.)]
    lines = record.add(columns, name='JUPITER', no_body=True)
    assert seen == [('phase_angle', 'JUPITER')]
    assert lines[0].endswith('  28.648,  57.296')


#===============================================================================
# Suite static / light helpers
#===============================================================================
def test_suite_add_tables_creates_four_tables() -> None:
    """add_tables registers the inventory, sky, ring, and body tables."""
    suite = Suite.__new__(Suite)
    suite.template_path = None  # type: ignore[assignment]
    suite.volume_id = 'GO_0001'
    suite.tables = []
    suite.add_tables(None)  # type: ignore[arg-type]
    qualifiers = [t.qualifier for t in suite.tables]
    # No 'sun': the sun table is not wired in (see tables.SunTable).
    assert qualifiers == ['inventory', 'sky', 'ring', 'body']


def test_suite_add_tables_names_summary_files(tmp_path: Any) -> None:
    """The suite's geometry tables carry level='summary', so they name real files.

    The level feeds both the output file name and the label template name, so a
    missing level yields <volume>_<kind>_None.tab and a template that does not
    exist -- invisible until a write is attempted.
    """
    suite = Suite.__new__(Suite)
    suite.template_path = None  # type: ignore[assignment]
    suite.volume_id = 'GO_0001'
    suite.tables = []
    suite.add_tables(tmp_path)

    by_qualifier = {t.qualifier: t for t in suite.tables}
    for qualifier in ('sky', 'ring', 'body'):
        assert by_qualifier[qualifier].level == 'summary'
        assert by_qualifier[qualifier].filename.name == f'GO_0001_{qualifier}_summary.tab'
    # The inventory table is level-free and names a .csv.
    assert by_qualifier['inventory'].level is None
    assert by_qualifier['inventory'].filename.name == 'GO_0001_inventory.csv'


def test_suite_make_record_builds_one_record(monkeypatch: pytest.MonkeyPatch) -> None:
    """make_record builds a single Record from the indexed observation."""
    suite = Suite.__new__(Suite)
    suite.observations = ['obs0']
    suite.volume_id = 'GO_0001'
    suite.meshgrids = {}
    suite.sampling = 8
    created: list[Any] = []
    monkeypatch.setattr(
        suite_mod, 'Record',
        lambda *args: created.append(args) or 'RECORD')  # type: ignore[func-returns-value]
    record = suite.make_record(0)
    assert record == 'RECORD'  # type: ignore[comparison-overlap]
    assert created == [('obs0', 'GO_0001', {}, 8)]


def test_suite_add_dispatches_to_every_table() -> None:
    """add() hands the record to every table in the suite."""
    suite = Suite.__new__(Suite)
    sky: Any = types.SimpleNamespace(added=[], add=lambda r: sky.added.append(r))
    inv: Any = types.SimpleNamespace(added=[], add=lambda r: inv.added.append(r))
    suite.tables = [sky, inv]
    rec = types.SimpleNamespace()
    suite.add(rec)  # type: ignore[arg-type]
    assert sky.added == [rec]
    assert inv.added == [rec]


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
    monkeypatch.setattr(Suite, 'make_record', lambda self, i: 'rec')
    monkeypatch.setattr(Suite, 'add', lambda self, record: added.append(record))
    monkeypatch.setattr(Suite, 'write',
                        lambda self, labels_only=False: written.append(labels_only))
    monkeypatch.setattr(config, 'cleanup', lambda: None, raising=False)
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda: None))
    suite.create()
    assert added == ['rec']
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
    monkeypatch.setattr(Suite, 'make_record', lambda self, i: 'rec')
    monkeypatch.setattr(Suite, 'add', lambda self, record: added.append(record))
    monkeypatch.setattr(Suite, 'write', lambda self, labels_only=False: None)
    monkeypatch.setattr(config, 'cleanup', lambda: None, raising=False)
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda: None))
    suite.create()
    # The lone observation does not match the glob -> nothing added.
    assert added == []
