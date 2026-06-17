################################################################################
# tests/test_index_support.py: IndexTable formatting/dispatch + _create_index.
################################################################################
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from filecache import FCPath
from pdsparser import PdsLabel

import metadata_tools.common as com
import metadata_tools.index_support as idx
import metadata_tools.util as util

IndexTable = idx.IndexTable


class FakePds3Table:
    """Minimal stand-in for pdstemplate.pds3table.Pds3Table.old_lookup."""

    def __init__(self, columns: list[dict[str, Any]]) -> None:
        # columns: list of dicts, each mapping keyword -> value (None if absent).
        self.columns = columns

    def old_lookup(self, key: str, colnum: int) -> Any:
        if colnum > len(self.columns):
            raise IndexError(colnum)
        return self.columns[colnum - 1].get(key)


#===============================================================================
# _format_value
#===============================================================================
def test_format_value_character_is_quoted_and_padded() -> None:
    assert IndexTable._format_value('IO', 'A10') == '"IO        "'


def test_format_value_real() -> None:
    assert IndexTable._format_value(3.14159, 'F8.3') == '   3.142'


def test_format_value_integer() -> None:
    assert IndexTable._format_value(42, 'I5') == '   42'


#===============================================================================
# _format_parms
#===============================================================================
def test_format_parms_character_width_includes_quotes() -> None:
    assert IndexTable._format_parms('A10') == (12, 'CHARACTER')


def test_format_parms_real() -> None:
    assert IndexTable._format_parms('F8.3') == (8, 'ASCII_REAL')


def test_format_parms_integer() -> None:
    # Integer formats hit the TypeError fallback path that re-formats with 0.
    assert IndexTable._format_parms('I5') == (5, 'ASCII_INTEGER')


#===============================================================================
# _get_null_value
#===============================================================================
def test_get_null_value_prefers_highest_priority_key() -> None:
    # When several null keywords are present, the highest-priority one wins.
    table = FakePds3Table([{'NULL_CONSTANT': '-999',
                            'NOT_APPLICABLE_CONSTANT': 'N/A'}])
    assert IndexTable._get_null_value(table, 1) == '-999'


def test_get_null_value_single_key() -> None:
    # A column with only one null keyword present returns that value.
    table = FakePds3Table([{'NULL_CONSTANT': '-999'}])
    assert IndexTable._get_null_value(table, 1) == '-999'


def test_get_null_value_lower_priority_key_when_only_one_present() -> None:
    # When only a lower-priority keyword is set, it is used.
    table = FakePds3Table([{'NOT_APPLICABLE_CONSTANT': 'N/A'}])
    assert IndexTable._get_null_value(table, 1) == 'N/A'


def test_get_null_value_none_when_no_keys() -> None:
    table = FakePds3Table([{}])
    assert IndexTable._get_null_value(table, 1) is None


#===============================================================================
# _get_column_values
#===============================================================================
def test_get_column_values_iterates_until_indexerror() -> None:
    table = FakePds3Table([
        {'NAME': 'A', 'FORMAT': 'A4', 'ITEMS': None, 'NULL_CONSTANT': '-'},
        {'NAME': 'B', 'FORMAT': 'I5', 'ITEMS': 2, 'NULL_CONSTANT': '0'},
    ])
    stubs = IndexTable._get_column_values(table)
    assert [s['NAME'] for s in stubs] == ['A', 'B']
    assert stubs[1]['ITEMS'] == 2


#===============================================================================
# _format_column
#===============================================================================
def test_format_column_multi_item_expands_and_joins() -> None:
    stub = {'NAME': 'X', 'FORMAT': '"A4"', 'ITEMS': 2, 'NULL_CONSTANT': '-'}
    assert IndexTable._format_column(stub, ['AB', 'CD']) == '"AB  ","CD  "'


def test_format_column_scrubs_whitespace_and_quotes() -> None:
    stub = {'NAME': 'X', 'FORMAT': '"A8"', 'ITEMS': None, 'NULL_CONSTANT': '-'}
    # Leading/trailing space stripped, newline -> space, doubled space
    # collapsed, embedded quotes removed.
    assert IndexTable._format_column(stub, '  a"b\n c  ') == '"ab c    "'


def test_format_column_invalid_format_warns_and_returns_stars() -> None:
    stub = {'NAME': 'X', 'FORMAT': '"F8.3"', 'ITEMS': None, 'NULL_CONSTANT': '-'}
    # A list value is incompatible with a real format -> TypeError fallback,
    # which logs a warning and returns a field of '*' the column width wide.
    result = IndexTable._format_column(stub, [1, 2])
    assert result == 8 * '*'


#===============================================================================
# _index_one_value dispatch
#===============================================================================
def _table_with_stub(stub: Any) -> Any:
    table = IndexTable.__new__(IndexTable)
    table.usage = {}
    return table


def test_index_one_value_builtin_key_function(monkeypatch: pytest.MonkeyPatch) -> None:
    table = _table_with_stub(None)
    stub = {'NAME': 'VOLUME_ID', 'NULL_CONSTANT': '-'}
    monkeypatch.setattr(idx.hconf,  # type: ignore[attr-defined]
                        'get_volume_id', lambda p: 'GO_0042')
    value = table._index_one_value(stub, FCPath('/x/GO_0042/a.lbl'), {})
    assert value == 'GO_0042'


def test_index_one_value_config_key_function(monkeypatch: pytest.MonkeyPatch) -> None:
    table = _table_with_stub(None)
    stub = {'NAME': 'SPECIAL', 'NULL_CONSTANT': '-'}
    monkeypatch.setattr(idx.config, 'key__special',  # type: ignore[attr-defined]
                        lambda path, d: 'computed', raising=False)
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {})
    assert value == 'computed'


def test_index_one_value_raw_label_value() -> None:
    table = _table_with_stub(None)
    stub = {'NAME': 'EXPOSURE', 'NULL_CONSTANT': '-'}
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {'EXPOSURE': 12})
    assert value == 12
    assert table.usage['EXPOSURE'] is True


def test_index_one_value_missing_becomes_null() -> None:
    table = _table_with_stub(None)
    stub = {'NAME': 'MISSING', 'NULL_CONSTANT': 'NULLVAL'}
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {})
    assert value == 'NULLVAL'


def test_index_one_value_none_result_becomes_null(monkeypatch: pytest.MonkeyPatch) -> None:
    table = _table_with_stub(None)
    stub = {'NAME': 'SPECIAL', 'NULL_CONSTANT': 'NULLVAL'}
    monkeypatch.setattr(idx.config, 'key__special',  # type: ignore[attr-defined]
                        lambda path, d: None, raising=False)
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {})
    assert value == 'NULLVAL'


def test_index_one_value_none_without_null_constant_raises(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # A key function returning None with no null constant cannot be represented;
    # a ValueError is raised (not a -O-stripped assert).
    table = _table_with_stub(None)
    stub = {'NAME': 'SPECIAL', 'NULL_CONSTANT': None}
    monkeypatch.setattr(idx.config, 'key__special',  # type: ignore[attr-defined]
                        lambda path, d: None, raising=False)
    with pytest.raises(ValueError, match='Null constant needed'):
        table._index_one_value(stub, FCPath('/x/a.lbl'), {})


#===============================================================================
# Built-in key functions
#===============================================================================
def test_key_volume_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(idx.hconf,  # type: ignore[attr-defined]
                        'get_volume_id', lambda p: 'GO_0001')
    assert idx.key__volume_id(FCPath('/x/GO_0001/a.lbl'), {}) == 'GO_0001'


def test_key_file_specification_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(idx.hconf,  # type: ignore[attr-defined]
                        'get_volume_id', lambda p: 'GO_0001')
    result = idx.key__file_specification_name(
        FCPath('/x/GO_0001/data/c0.lbl'), {})
    assert result.as_posix() == 'data/c0.lbl'


#===============================================================================
# IndexTable.add
#===============================================================================
def test_add_writes_one_row(monkeypatch: pytest.MonkeyPatch) -> None:
    table = IndexTable.__new__(IndexTable)
    table.usage = {}
    table.rows = []
    table.column_stubs = [
        {'NAME': 'VOLUME_ID', 'FORMAT': '"A8"', 'ITEMS': None, 'NULL_CONSTANT': '-'},
        {'NAME': 'EXPOSURE', 'FORMAT': '"F8.3"', 'ITEMS': None, 'NULL_CONSTANT': '-999'},
    ]
    monkeypatch.setattr(idx.hconf,  # type: ignore[attr-defined]
                        'get_volume_id', lambda p: 'GO_0001')

    fake_label = types.SimpleNamespace(as_dict=lambda: {'EXPOSURE': 1.5})
    monkeypatch.setattr(PdsLabel, 'from_file',
                        staticmethod(lambda path: fake_label))
    table.add(FCPath('/x/GO_0001'), 'c0.lbl')
    assert len(table.rows) == 1
    assert table.rows[0].startswith('"GO_0001 "')


#===============================================================================
# IndexTable construction early-return
#===============================================================================
def test_indextable_without_input_dir_returns_early() -> None:
    table = IndexTable(qualifier='supplemental')
    assert table.qualifier == 'supplemental'
    assert not hasattr(table, 'files')


#===============================================================================
# _create_index walk
#===============================================================================
def test_create_index_processes_each_volume(
        monkeypatch: pytest.MonkeyPatch,
        tmp_volume_tree: Callable[..., FCPath]) -> None:
    tree = tmp_volume_tree(files={'_index.tab': ['x']})
    processed: list[Any] = []
    # Per-volume "unused" sets; the cross-volume intersection is {'COLA'}.
    unused_by_volume = {'GO_0001': {'COLA', 'COLB'}, 'GO_0002': {'COLA'}}

    class FakeIndexTable:
        def __init__(self, indir: Any, outdir: Any, template_path: Any,
                     metadata_dir: Any, **kwargs: Any) -> None:
            vol: str = kwargs['volume_id']
            processed.append(vol)
            self.unused = set(unused_by_volume[vol])

        def create(self, labels_only: bool = False, pattern: Any = None) -> None:
            pass

    closes: list[bool] = []
    warnings: list[Any] = []
    monkeypatch.setattr(idx, 'IndexTable', FakeIndexTable)
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None,
                            warning=lambda msg, arg: warnings.append(arg),
                            close=lambda **k: closes.append(True)))
    idx._create_index(tree, tree, FCPath('/tmpl.lbl'))
    assert sorted(processed) == ['GO_0001', 'GO_0002']
    # The logger is closed exactly once (after the walk), not once per directory.
    assert closes == [True]
    # The unused-columns warning reflects the cross-volume intersection.
    assert warnings == [{'COLA'}]


def test_create_index_task_list_only(
        monkeypatch: pytest.MonkeyPatch,
        tmp_volume_tree: Callable[..., FCPath]) -> None:
    tree = tmp_volume_tree(files={'_index.tab': ['x']})
    added: list[Any] = []
    monkeypatch.setattr(com, 'add_task', lambda vol, col: added.append(vol))
    monkeypatch.setattr(com, 'write_task_file', lambda f: None)
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda **k: None))
    idx._create_index(tree, tree, FCPath('/tmpl.lbl'),
                      task_list_only=True, task_file='tasks.json')
    assert sorted(added) == ['GO_0001', 'GO_0002']


#===============================================================================
# IndexTable.__init__ full paths
#===============================================================================
def _patch_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(com, 'init_logger', lambda d, t: None)
    monkeypatch.setattr(util, 'read_txt_file',
                        lambda path, as_string=False: 'TEMPLATE')
    monkeypatch.setattr(idx, 'Pds3Table',
                        lambda *a, **k: FakePds3Table([
                            {'NAME': 'VOLUME_ID', 'FORMAT': 'A8', 'ITEMS': None,
                             'NULL_CONSTANT': '-'}]))
    monkeypatch.setattr(idx.hconf,  # type: ignore[attr-defined]
                        'get_volume_id', lambda p: 'GO_0001')


def test_indextable_init_primary_path(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    indir = tmp_path / 'GO_0001'
    (indir / 'data').mkdir(parents=True)
    (indir / 'data' / 'c0.LBL').write_text('x', encoding='utf-8')
    outdir = tmp_path / 'out'
    outdir.mkdir()
    _patch_template(monkeypatch)
    table = IndexTable(FCPath(indir), FCPath(outdir), FCPath('/tmpl.lbl'),
                       FCPath(outdir), qualifier='', volume_id='GO_0001')
    # create_primary path: file list built from the directory tree.
    assert len(table.files) == 1
    assert table.column_stubs[0]['NAME'] == 'VOLUME_ID'


def test_indextable_init_supplemental_path(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    indir = tmp_path / 'GO_0001'
    indir.mkdir()
    meta = tmp_path / 'meta'
    meta.mkdir()
    (meta / 'GO_0001_index.lbl').write_text('x', encoding='utf-8')
    outdir = tmp_path / 'out'
    outdir.mkdir()
    _patch_template(monkeypatch)
    monkeypatch.setattr(util, 'pds_table', lambda lbl: types.SimpleNamespace(
        dicts_by_row=lambda: [{'FILE_SPECIFICATION_NAME': 'data/c0.IMG'}]))
    table = IndexTable(FCPath(indir), FCPath(outdir), FCPath('/tmpl.lbl'),
                       FCPath(meta), qualifier='supplemental', volume_id='GO_0001')
    assert table.files[0].name == 'c0.LBL'


def test_indextable_init_supplemental_missing_primary_raises(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    indir = tmp_path / 'GO_0001'
    indir.mkdir()
    meta = tmp_path / 'meta'
    meta.mkdir()
    monkeypatch.setattr(idx.hconf,  # type: ignore[attr-defined]
                        'get_volume_id', lambda p: 'GO_0001')
    with pytest.raises(FileNotFoundError):
        IndexTable(FCPath(indir), FCPath(indir), FCPath('/tmpl.lbl'),
                   FCPath(meta), qualifier='supplemental', volume_id='GO_0001')


#===============================================================================
# IndexTable.create
#===============================================================================
def test_create_iterates_matching_files(monkeypatch: pytest.MonkeyPatch) -> None:
    table = IndexTable.__new__(IndexTable)
    table.glob = 'C0*.LBL'
    table.volume_id = 'GO_0001'
    table.usage = {'COLA': False}
    table.unused = set()
    table.rows = []
    table.filename = None  # type: ignore[assignment]
    table.files = [FCPath('/x/GO_0001/data/C0123.LBL'),
                   FCPath('/x/GO_0001/data/SKIP.TXT')]
    added: list[Any] = []
    monkeypatch.setattr(IndexTable, 'add',
                        lambda self, root, name: added.append(name))
    monkeypatch.setattr(IndexTable, 'write', lambda self, labels_only=False: None)
    monkeypatch.setattr(idx.hconf,  # type: ignore[attr-defined]
                        'get_volume_id', lambda p: 'GO_0001')
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))
    table.create()
    assert added == ['C0123.LBL']
    # COLA never had a non-null value -> flagged unused.
    assert 'COLA' in table.unused


def test_create_returns_without_files() -> None:
    table = IndexTable.__new__(IndexTable)
    # create() is typed -> None; the test asserts the early-return value anyway.
    assert table.create() is None  # type: ignore[func-returns-value]


#===============================================================================
# get_args
#===============================================================================
def test_get_args_parses_type() -> None:
    parser = idx.get_args(host='GO', index_type='supplemental')
    args = parser.parse_args(['/vol', '/meta', '/out', '--type', 'raw'])
    assert args.type == 'raw'


#===============================================================================
# process_index wiring
#===============================================================================
def test_process_index_task_output_sets_task_list(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(idx, '_create_index', lambda *a, **k: captured.update(k))
    args = types.SimpleNamespace(volume_tree='/v', output_tree='/o',
                                 metadata_tree='/m', volumes=None,
                                 labels=False, type='supplemental',
                                 pattern=None, task_output='tasks.json')
    # SimpleNamespace stands in for the argparse.Namespace process_index expects.
    idx.process_index('GO_0xxx_supplemental_index', args=args)  # type: ignore[arg-type]
    assert captured['task_list_only'] is True
    assert captured['task_file'] == 'tasks.json'


#===============================================================================
# process_index wiring (original)
#===============================================================================
def test_process_index_invokes_create_index(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(idx, '_create_index',
                        lambda *a, **k: captured.update(k))
    args = types.SimpleNamespace(volume_tree='/v', output_tree='/o',
                                 metadata_tree='/m', volumes=['GO_0001'],
                                 labels=False, type='supplemental',
                                 pattern=None, task_output=None)
    # SimpleNamespace stands in for the argparse.Namespace process_index expects.
    idx.process_index('GO_0xxx_supplemental_index', args=args)  # type: ignore[arg-type]
    assert captured['qualifier'] == 'supplemental'
    assert captured['volumes'] == ['GO_0001']
