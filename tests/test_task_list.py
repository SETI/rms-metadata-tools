################################################################################
# tests/test_task_list.py: Tests for metadata_tools.task_list
################################################################################
"""Tests for task_list: make_task, task_generator, scan_volumes, write_task_file."""
import json
from pathlib import Path

from filecache import FCPath

import metadata_tools.task_list_support as tl


#===============================================================================
# make_task
#===============================================================================
def test_make_task_structure() -> None:
    task = tl.make_task('GO_0017')
    assert task == {'task_id': 'task-GO_0017', 'data': {'volume_id': 'GO_0017'}}


def test_make_task_data_volume_id() -> None:
    assert tl.make_task('GO_0001')['data']['volume_id'] == 'GO_0001'


#===============================================================================
# task_generator
#===============================================================================
def test_task_generator_yields_one_per_volume() -> None:
    tasks = list(tl.task_generator(['GO_0001', 'GO_0002']))
    assert len(tasks) == 2
    assert tasks[0]['data']['volume_id'] == 'GO_0001'
    assert tasks[1]['data']['volume_id'] == 'GO_0002'


def test_task_generator_empty() -> None:
    assert list(tl.task_generator([])) == []


def test_task_generator_task_ids() -> None:
    tasks = list(tl.task_generator(['GO_0001', 'GO_0002']))
    assert tasks[0]['task_id'] == 'task-GO_0001'
    assert tasks[1]['task_id'] == 'task-GO_0002'


def test_task_generator_is_reusable() -> None:
    # Calling task_generator twice produces independent iterators.
    vols = ['GO_0001']
    assert list(tl.task_generator(vols)) == list(tl.task_generator(vols))


#===============================================================================
# scan_volumes
#===============================================================================
def _make_tree(tmp_path: Path, volumes: list[str]) -> FCPath:
    """Create a fake GO_0xxx collection tree under tmp_path."""
    col = tmp_path / 'GO_0xxx'
    for vol in volumes:
        (col / vol).mkdir(parents=True)
    return FCPath(col)


def test_scan_volumes_finds_matching_directories(tmp_path: Path) -> None:
    tree = _make_tree(tmp_path, ['GO_0001', 'GO_0002', 'GO_0017'])
    assert tl.scan_volumes(tree) == ['GO_0001', 'GO_0002', 'GO_0017']


def test_scan_volumes_returns_sorted(tmp_path: Path) -> None:
    tree = _make_tree(tmp_path, ['GO_0017', 'GO_0001', 'GO_0003'])
    assert tl.scan_volumes(tree) == ['GO_0001', 'GO_0003', 'GO_0017']


def test_scan_volumes_skips_non_matching_dirs(tmp_path: Path) -> None:
    col = tmp_path / 'GO_0xxx'
    (col / 'GO_0001').mkdir(parents=True)
    (col / 'not_a_volume').mkdir()
    result = tl.scan_volumes(FCPath(col))
    assert 'not_a_volume' not in result
    assert 'GO_0001' in result


def test_scan_volumes_skips_skip_dir(tmp_path: Path) -> None:
    col = tmp_path / 'GO_0xxx'
    (col / 'GO_0001').mkdir(parents=True)
    (col / '__skip' / 'GO_0002').mkdir(parents=True)
    result = tl.scan_volumes(FCPath(col))
    assert result == ['GO_0001']


def test_scan_volumes_empty_tree(tmp_path: Path) -> None:
    col = tmp_path / 'GO_0xxx'
    col.mkdir()
    assert tl.scan_volumes(FCPath(col)) == []


#===============================================================================
# write_task_file
#===============================================================================
def test_write_task_file_creates_valid_json(tmp_path: Path) -> None:
    out = tmp_path / 'tasks.json'
    tl.write_task_file(['GO_0001', 'GO_0002'], str(out))
    data = json.loads(out.read_text(encoding='utf-8'))
    assert len(data) == 2
    assert data[0] == {'task_id': 'task-GO_0001', 'data': {'volume_id': 'GO_0001'}}
    assert data[1] == {'task_id': 'task-GO_0002', 'data': {'volume_id': 'GO_0002'}}


def test_write_task_file_empty(tmp_path: Path) -> None:
    out = tmp_path / 'empty.json'
    tl.write_task_file([], str(out))
    assert json.loads(out.read_text(encoding='utf-8')) == []


def test_write_task_file_accepts_fcpath(tmp_path: Path) -> None:
    out = FCPath(tmp_path / 'tasks.json')
    tl.write_task_file(['GO_0001'], out)
    data = json.loads((tmp_path / 'tasks.json').read_text(encoding='utf-8'))
    assert data[0]['data']['volume_id'] == 'GO_0001'
