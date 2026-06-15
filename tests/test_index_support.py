################################################################################
# tests/test_index_support.py: IndexTable formatting/dispatch + _create_index.
################################################################################
import types

import pytest
from filecache import FCPath

import metadata_tools.index_formats as idxf
import metadata_tools.index_support as idx

IndexTable = idx.IndexTable


class FakePds3Table:
    """Minimal stand-in for pdstemplate.pds3table.Pds3Table.old_lookup."""

    def __init__(self, columns):
        # columns: list of dicts, each mapping keyword -> value (None if absent).
        self.columns = columns

    def old_lookup(self, key, colnum):
        if colnum > len(self.columns):
            raise IndexError(colnum)
        return self.columns[colnum - 1].get(key)


#===============================================================================
# _format_value
#===============================================================================
def test_format_value_character_is_quoted_and_padded():
    assert idxf._format_value('IO', 'A10') == '"IO        "'


def test_format_value_real():
    assert idxf._format_value(3.14159, 'F8.3') == '   3.142'


def test_format_value_integer():
    assert idxf._format_value(42, 'I5') == '   42'


#===============================================================================
# _format_parms
#===============================================================================
def test_format_parms_character_width_includes_quotes():
    assert idxf._format_parms('A10') == (12, 'CHARACTER')


def test_format_parms_real():
    assert idxf._format_parms('F8.3') == (8, 'ASCII_REAL')


def test_format_parms_integer():
    # Integer formats hit the TypeError fallback path that re-formats with 0.
    assert idxf._format_parms('I5') == (5, 'ASCII_INTEGER')


#===============================================================================
# _get_null_value  [BUG]
#===============================================================================
def test_get_null_value_returns_last_present_key():
    # Current behavior: the lowest-priority key present wins (the loop uses
    # `continue` where it means `break`).
    table = FakePds3Table([{'NULL_CONSTANT': '-999',
                            'NOT_APPLICABLE_CONSTANT': 'N/A'}])
    assert idxf._get_null_value(table, 1) == 'N/A'


@pytest.mark.xfail(strict=True, reason='BUG: _get_null_value uses continue '
                   'instead of break, so the highest-priority null keyword is '
                   'not returned; a column with only NULL_CONSTANT set yields None.')
def test_get_null_value_prefers_highest_priority_key():
    table = FakePds3Table([{'NULL_CONSTANT': '-999'}])
    assert idxf._get_null_value(table, 1) == '-999'


#===============================================================================
# _get_column_values
#===============================================================================
def test_get_column_values_iterates_until_indexerror():
    table = FakePds3Table([
        {'NAME': 'A', 'FORMAT': 'A4', 'ITEMS': None, 'NULL_CONSTANT': '-'},
        {'NAME': 'B', 'FORMAT': 'I5', 'ITEMS': 2, 'NULL_CONSTANT': '0'},
    ])
    stubs = idxf._get_column_values(table)
    assert [s['NAME'] for s in stubs] == ['A', 'B']
    assert stubs[1]['ITEMS'] == 2


#===============================================================================
# _format_column
#===============================================================================
def test_format_column_multi_item_expands_and_joins():
    stub = {'NAME': 'X', 'FORMAT': '"A4"', 'ITEMS': 2, 'NULL_CONSTANT': '-'}
    assert idxf._format_column(stub, ['AB', 'CD']) == '"AB  ","CD  "'


def test_format_column_scrubs_whitespace_and_quotes():
    stub = {'NAME': 'X', 'FORMAT': '"A8"', 'ITEMS': None, 'NULL_CONSTANT': '-'}
    # Leading/trailing space stripped, newline -> space, doubled space
    # collapsed, embedded quotes removed.
    assert idxf._format_column(stub, '  a"b\n c  ') == '"ab c    "'


def test_format_column_invalid_format_warns_and_returns_stars():
    stub = {'NAME': 'X', 'FORMAT': '"F8.3"', 'ITEMS': None, 'NULL_CONSTANT': '-'}
    # A list value is incompatible with a real format -> TypeError fallback,
    # which logs a warning and returns a field of '*' the column width wide.
    result = idxf._format_column(stub, [1, 2])
    assert result == 8 * '*'


#===============================================================================
# _index_one_value dispatch
#===============================================================================
def _table_with_stub(stub):
    table = IndexTable.__new__(IndexTable)
    table.usage = {}
    return table


def test_index_one_value_builtin_key_function(monkeypatch):
    table = _table_with_stub(None)
    stub = {'NAME': 'VOLUME_ID', 'NULL_CONSTANT': '-'}
    monkeypatch.setattr(idx.hconf, 'get_volume_id', lambda p: 'GO_0042')
    value = table._index_one_value(stub, FCPath('/x/GO_0042/a.lbl'), {})
    assert value == 'GO_0042'


def test_index_one_value_config_key_function(monkeypatch):
    table = _table_with_stub(None)
    stub = {'NAME': 'SPECIAL', 'NULL_CONSTANT': '-'}
    monkeypatch.setattr(idx.config, 'key__special',
                        lambda path, d: 'computed', raising=False)
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {})
    assert value == 'computed'


def test_index_one_value_raw_label_value():
    table = _table_with_stub(None)
    stub = {'NAME': 'EXPOSURE', 'NULL_CONSTANT': '-'}
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {'EXPOSURE': 12})
    assert value == 12
    assert table.usage['EXPOSURE'] is True


def test_index_one_value_missing_becomes_null():
    table = _table_with_stub(None)
    stub = {'NAME': 'MISSING', 'NULL_CONSTANT': 'NULLVAL'}
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {})
    assert value == 'NULLVAL'


def test_index_one_value_none_result_becomes_null(monkeypatch):
    table = _table_with_stub(None)
    stub = {'NAME': 'SPECIAL', 'NULL_CONSTANT': 'NULLVAL'}
    monkeypatch.setattr(idx.config, 'key__special',
                        lambda path, d: None, raising=False)
    value = table._index_one_value(stub, FCPath('/x/a.lbl'), {})
    assert value == 'NULLVAL'


#===============================================================================
# Built-in key functions
#===============================================================================
def test_key_volume_id(monkeypatch):
    monkeypatch.setattr(idx.hconf, 'get_volume_id', lambda p: 'GO_0001')
    assert idx.key__volume_id(FCPath('/x/GO_0001/a.lbl'), {}) == 'GO_0001'


def test_key_file_specification_name(monkeypatch):
    monkeypatch.setattr(idx.hconf, 'get_volume_id', lambda p: 'GO_0001')
    result = idx.key__file_specification_name(
        FCPath('/x/GO_0001/data/c0.lbl'), {})
    assert result.as_posix() == 'data/c0.lbl'


#===============================================================================
# IndexTable.add
#===============================================================================
def test_add_writes_one_row(monkeypatch):
    table = IndexTable.__new__(IndexTable)
    table.usage = {}
    table.rows = []
    table.column_stubs = [
        {'NAME': 'VOLUME_ID', 'FORMAT': '"A8"', 'ITEMS': None, 'NULL_CONSTANT': '-'},
        {'NAME': 'EXPOSURE', 'FORMAT': '"F8.3"', 'ITEMS': None, 'NULL_CONSTANT': '-999'},
    ]
    monkeypatch.setattr(idx.hconf, 'get_volume_id', lambda p: 'GO_0001')

    fake_label = types.SimpleNamespace(as_dict=lambda: {'EXPOSURE': 1.5})
    monkeypatch.setattr(idx.PdsLabel, 'from_file',
                        staticmethod(lambda path: fake_label))
    table.add(FCPath('/x/GO_0001'), 'c0.lbl')
    assert len(table.rows) == 1
    assert table.rows[0].startswith('"GO_0001 "')


#===============================================================================
# IndexTable construction early-return
#===============================================================================
def test_indextable_without_input_dir_returns_early():
    table = IndexTable(qualifier='supplemental')
    assert table.qualifier == 'supplemental'
    assert not hasattr(table, 'files')


#===============================================================================
# _create_index walk
#===============================================================================
def test_create_index_processes_each_volume(monkeypatch, tmp_volume_tree):
    tree = tmp_volume_tree(files={'_index.tab': ['x']})
    processed = []

    class FakeIndexTable:
        def __init__(self, indir, outdir, template_path, metadata_dir, **kwargs):
            self.unused = {'COLA'}
            processed.append(kwargs.get('volume_id'))

        def create(self, labels_only=False, pattern=None):
            pass

    monkeypatch.setattr(idx, 'IndexTable', FakeIndexTable)
    monkeypatch.setattr(idx.com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda **k: None))
    idx._create_index(tree, tree, FCPath('/tmpl.lbl'))
    assert sorted(processed) == ['GO_0001', 'GO_0002']


def test_create_index_task_list_only(monkeypatch, tmp_volume_tree):
    tree = tmp_volume_tree(files={'_index.tab': ['x']})
    added = []
    monkeypatch.setattr(idx.com, 'add_task', lambda vol, col: added.append(vol))
    monkeypatch.setattr(idx.com, 'write_task_file', lambda f: None)
    monkeypatch.setattr(idx.com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda **k: None))
    idx._create_index(tree, tree, FCPath('/tmpl.lbl'),
                      task_list_only=True, task_file='tasks.json')
    assert sorted(added) == ['GO_0001', 'GO_0002']


#===============================================================================
# IndexTable.__init__ full paths
#===============================================================================
def _patch_template(monkeypatch):
    monkeypatch.setattr(idx.com, 'init_logger', lambda d, t: None)
    monkeypatch.setattr(idx.util, 'read_txt_file',
                        lambda path, as_string=False: 'TEMPLATE')
    monkeypatch.setattr(idx, 'Pds3Table',
                        lambda *a, **k: FakePds3Table([
                            {'NAME': 'VOLUME_ID', 'FORMAT': 'A8', 'ITEMS': None,
                             'NULL_CONSTANT': '-'}]))
    monkeypatch.setattr(idx.hconf, 'get_volume_id', lambda p: 'GO_0001')


def test_indextable_init_primary_path(monkeypatch, tmp_path):
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


def test_indextable_init_supplemental_path(monkeypatch, tmp_path):
    indir = tmp_path / 'GO_0001'
    indir.mkdir()
    meta = tmp_path / 'meta'
    meta.mkdir()
    (meta / 'GO_0001_index.lbl').write_text('x', encoding='utf-8')
    outdir = tmp_path / 'out'
    outdir.mkdir()
    _patch_template(monkeypatch)
    monkeypatch.setattr(idx.util, 'PdsTable', lambda lbl: types.SimpleNamespace(
        dicts_by_row=lambda: [{'FILE_SPECIFICATION_NAME': 'data/c0.IMG'}]))
    table = IndexTable(FCPath(indir), FCPath(outdir), FCPath('/tmpl.lbl'),
                       FCPath(meta), qualifier='supplemental', volume_id='GO_0001')
    assert table.files[0].name == 'c0.LBL'


def test_indextable_init_supplemental_missing_primary_raises(monkeypatch, tmp_path):
    indir = tmp_path / 'GO_0001'
    indir.mkdir()
    meta = tmp_path / 'meta'
    meta.mkdir()
    monkeypatch.setattr(idx.hconf, 'get_volume_id', lambda p: 'GO_0001')
    with pytest.raises(FileNotFoundError):
        IndexTable(FCPath(indir), FCPath(indir), FCPath('/tmpl.lbl'),
                   FCPath(meta), qualifier='supplemental', volume_id='GO_0001')


#===============================================================================
# IndexTable.create
#===============================================================================
def test_create_iterates_matching_files(monkeypatch):
    table = IndexTable.__new__(IndexTable)
    table.glob = 'C0*.LBL'
    table.volume_id = 'GO_0001'
    table.usage = {'COLA': False}
    table.unused = set()
    table.rows = []
    table.filename = None
    table.files = [FCPath('/x/GO_0001/data/C0123.LBL'),
                   FCPath('/x/GO_0001/data/SKIP.TXT')]
    added = []
    monkeypatch.setattr(IndexTable, 'add',
                        lambda self, root, name: added.append(name))
    monkeypatch.setattr(IndexTable, 'write', lambda self, labels_only=False: None)
    monkeypatch.setattr(idx.hconf, 'get_volume_id', lambda p: 'GO_0001')
    monkeypatch.setattr(idx.com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))
    table.create()
    assert added == ['C0123.LBL']
    # COLA never had a non-null value -> flagged unused.
    assert 'COLA' in table.unused


def test_create_returns_without_files():
    table = IndexTable.__new__(IndexTable)
    assert table.create() is None


#===============================================================================
# get_args
#===============================================================================
def test_get_args_parses_type():
    parser = idx.get_args(host='GO', index_type='supplemental')
    args = parser.parse_args(['/vol', '/meta', '/out', '--type', 'raw'])
    assert args.type == 'raw'


#===============================================================================
# process_index wiring
#===============================================================================
def test_process_index_task_output_sets_task_list(monkeypatch):
    captured = {}
    monkeypatch.setattr(idx, '_create_index', lambda *a, **k: captured.update(k))
    args = types.SimpleNamespace(volume_tree='/v', output_tree='/o',
                                 metadata_tree='/m', volumes=None,
                                 labels=False, type='supplemental',
                                 pattern=None, task_output='tasks.json')
    idx.process_index('GO_0xxx_supplemental_index', args=args)
    assert captured['task_list_only'] is True
    assert captured['task_file'] == 'tasks.json'


#===============================================================================
# process_index wiring (original)
#===============================================================================
def test_process_index_invokes_create_index(monkeypatch):
    captured = {}
    monkeypatch.setattr(idx, '_create_index',
                        lambda *a, **k: captured.update(k))
    args = types.SimpleNamespace(volume_tree='/v', output_tree='/o',
                                 metadata_tree='/m', volumes=['GO_0001'],
                                 labels=False, type='supplemental',
                                 pattern=None, task_output=None)
    idx.process_index('GO_0xxx_supplemental_index', args=args)
    assert captured['qualifier'] == 'supplemental'
    assert captured['volumes'] == ['GO_0001']
