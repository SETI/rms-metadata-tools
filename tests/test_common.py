################################################################################
# tests/test_common.py: Table, PathAction, args, task list, logger.
################################################################################
import types
from collections.abc import Iterator
from pathlib import Path

import pdslogger
import pytest
from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.label_support as lab
import metadata_tools.util as util


@pytest.fixture(autouse=True)
def _reset_task_list() -> Iterator[None]:
    # task_list is a module global; keep these tests isolated and ordered.
    com.task_list.clear()
    yield
    com.task_list.clear()


#===============================================================================
# Table.__init__
#===============================================================================
def test_table_filename_default_suffix(tmp_path: Path) -> None:
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      level='summary', qualifier='body')
    assert table.filename.name == 'GO_0001_body_summary.tab'


def test_table_explicit_suffix(tmp_path: Path) -> None:
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      qualifier='inventory', suffix='_inventory.csv')
    assert table.filename.name == 'GO_0001_inventory.csv'


def test_table_without_output_dir_has_no_filename() -> None:
    table = com.Table(qualifier='body', level='summary')
    assert not hasattr(table, 'filename')
    assert table.rows == []


#===============================================================================
# Table.write
#===============================================================================
def test_write_empty_rows_returns_early(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
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
    table = com.Table(output_dir=FCPath(tmp_path), volume_id='GO_0001',
                      qualifier='body', level='summary')
    calls = []
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda path, rows: calls.append(('write', rows)))
    monkeypatch.setattr(util, 'dbprint', lambda msg: calls.append(('db', msg)))
    monkeypatch.setattr(lab, 'create',
                        lambda *a, **k: calls.append(('label', k.get('table_type'))))
    table.rows = ['row1']
    table.write()
    assert ('write', ['row1']) in calls
    assert ('label', 'body_summary') in calls


def test_write_labels_only_skips_table(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
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
    parser = com.get_common_args(host='GO')
    args = parser.parse_args(['gs://bucket//a///b', '/m', '/o'])
    assert args.volume_tree == 'gs://bucket/a/b'


#===============================================================================
# get_common_args
#===============================================================================
def test_get_common_args_skips_volume_when_none() -> None:
    parser = com.get_common_args(host='GO', volume_arg=None)
    args = parser.parse_args(['/meta', '/out'])
    assert not hasattr(args, 'volume_tree')
    assert args.metadata_tree == '/meta'


def test_get_common_args_flags() -> None:
    parser = com.get_common_args(host='GO')
    args = parser.parse_args(['/v', '/m', '/o', '--labels',
                              '--volumes', 'GO_0001', 'GO_0002'])
    assert args.labels is True
    assert args.volumes == ['GO_0001', 'GO_0002']


#===============================================================================
# task list
#===============================================================================
def test_add_task_appends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))
    com.add_task('GO_0001', 'index')
    assert com.task_list == [
        {'task_id': 'index-task-GO_0001', 'data': {'volume_id': 'GO_0001'}}]


def test_task_source_yields_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))
    com.add_task('GO_0002', 'geometry')
    assert list(com.task_source()) == com.task_list


def test_write_task_file_writes_json(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))
    com.add_task('GO_0001', 'index')
    target = tmp_path / 'tasks.json'
    com.write_task_file(str(target))
    assert 'GO_0001' in target.read_text(encoding='utf-8')


def test_write_task_file_noop_without_path() -> None:
    # write_task_file() is typed -> None; assert it runs without error and
    # yields None for a None path. (func-returns-value: the -> None return is
    # exactly what this test checks.)
    assert com.write_task_file(None) is None  # type: ignore[func-returns-value]


#===============================================================================
# init_logger
#===============================================================================
def test_init_logger_registers_handlers(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
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
