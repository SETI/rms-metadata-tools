################################################################################
# tests/test_common.py: Table, PathAction, args, task list, logger.
################################################################################
"""Tests for common: Table, PathAction, get_common_args, and init_logger."""
import types
from pathlib import Path

import pdslogger
import pytest
from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.label_support as lab
import metadata_tools.util as util


#===============================================================================
# Table.__init__
#===============================================================================
def test_table_filename_default_suffix(tmp_path: Path) -> None:
    """The default filename is <volume>_<qualifier>_<level>.tab."""
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      level='summary', qualifier='body')
    assert table.filename.name == 'GO_0001_body_summary.tab'


def test_table_explicit_suffix(tmp_path: Path) -> None:
    """An explicit suffix overrides the default table filename suffix."""
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      qualifier='inventory', suffix='_inventory.csv')
    assert table.filename.name == 'GO_0001_inventory.csv'


def test_table_without_output_dir_has_no_filename() -> None:
    """Without an output dir, no filename is set and rows start empty."""
    table = com.Table(qualifier='body', level='summary')
    assert not hasattr(table, 'filename')
    assert table.rows == []


#===============================================================================
# Table.write
#===============================================================================
def test_write_empty_rows_returns_early(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
    """write() with no rows writes neither table nor label."""
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      qualifier='body', level='summary')
    wrote = []
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda *a, **k: wrote.append(a))
    monkeypatch.setattr(lab, 'create', lambda *a, **k: wrote.append('label'))
    table.rows = []
    table.write()
    assert wrote == []


def test_write_table_and_label(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
    """write() writes the rows and creates a label of the matching table type."""
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      qualifier='body', level='summary')
    calls = []
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda path, rows: calls.append(('write', rows)))
    monkeypatch.setattr(lab, 'create',
                        lambda *a, **k: calls.append(('label', k.get('table_type'))))
    table.rows = ['row1']
    table.write()
    assert ('write', ['row1']) in calls
    assert ('label', 'body_summary') in calls


def test_write_labels_only_skips_table(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
    """write(labels_only=True) creates only the label, never the table file."""
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      qualifier='inventory', suffix='_inventory.csv',
                      use_global_template=True)
    calls = []
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda *a: calls.append('write'))
    monkeypatch.setattr(lab, 'create', lambda *a, **k: calls.append('label'))
    table.rows = []
    table.write(labels_only=True)
    assert calls == ['label']


#===============================================================================
# PathAction
#===============================================================================
def test_path_action_collapses_slashes_preserves_scheme() -> None:
    """Repeated slashes are collapsed while the URL scheme's // survives."""
    parser = com.get_common_args(host='GO')
    args = parser.parse_args(['gs://bucket//a///b', '/m', '/o'])
    assert args.volume_tree == 'gs://bucket/a/b'


#===============================================================================
# get_common_args
#===============================================================================
def test_get_common_args_skips_volume_when_none() -> None:
    """volume_arg=None omits the volume_tree positional from the parser."""
    parser = com.get_common_args(host='GO', volume_arg=None)
    args = parser.parse_args(['/meta', '/out'])
    assert not hasattr(args, 'volume_tree')
    assert args.metadata_tree == '/meta'


def test_get_common_args_flags() -> None:
    """--labels and multi-value --volumes parse into the namespace."""
    parser = com.get_common_args(host='GO')
    args = parser.parse_args(['/v', '/m', '/o', '--labels',
                              '--volumes', 'GO_0001', 'GO_0002'])
    assert args.labels is True
    assert args.volumes == ['GO_0001', 'GO_0002']


#===============================================================================
# init_logger
#===============================================================================
def test_init_logger_registers_handlers(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
    """init_logger registers the stdout handler alongside the file handler."""
    handlers = []
    fake_logger = types.SimpleNamespace(
        add_handler=lambda h: handlers.append(h),
        log=lambda level, msg, *a: handlers.append(('log', msg)))
    monkeypatch.setattr(com, '_LOGGER', fake_logger)
    monkeypatch.setattr(pdslogger, 'file_handler',
                        lambda path, level: ('file', path))
    monkeypatch.setattr(pdslogger, 'STDOUT_HANDLER', ('stdout',))
    com.init_logger(FCPath(tmp_path), 'index')
    assert ('stdout',) in handlers
