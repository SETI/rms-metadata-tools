################################################################################
# tests/test_cli_workers.py: the per-task callables shipped to cloud Workers
################################################################################
"""Tests for _IndexTask, _GeometryTask, and _CumulativeTask.

Each task runs on a cloud VM inside a private, auto-deleting FileCache so that
downloaded inputs are reclaimed per task (the global cache never evicts and
would exhaust the boot disk). These tests pin that wiring, the remote-path
rewrites through the cache, and the arguments handed to the engine.
"""
import argparse
import types
from typing import Any, ClassVar

import filecache
import pytest

import metadata_tools.cli.cumulative_worker as cum_worker
import metadata_tools.cli.geometry_worker as geom_worker
import metadata_tools.cli.index_worker as idx_worker
import metadata_tools.cumulative_support
import metadata_tools.geometry_support
import metadata_tools.index_support


class _CacheStub:
    """Stand-in for filecache.FileCache recording construction and new_path calls."""

    instances: ClassVar[list['_CacheStub']] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.exited = False
        _CacheStub.instances.append(self)

    def __enter__(self) -> '_CacheStub':
        return self

    def __exit__(self, *exc: Any) -> None:
        self.exited = True

    def new_path(self, path: str) -> str:
        return f'cached:{path}'


@pytest.fixture
def engine_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...],
                                                                dict[str, Any]]]:
    """Stub FileCache, set_host, and the three engine entry points.

    Returns:
        The list into which each engine call is recorded as (name, args, kwargs).
    """
    _CacheStub.instances = []
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(filecache, 'FileCache', _CacheStub)
    for module in (idx_worker, geom_worker, cum_worker):
        monkeypatch.setattr(module, 'set_host', lambda host_id: None)
    for package, name in ((metadata_tools.index_support, 'process_index'),
                          (metadata_tools.geometry_support, 'process_tables'),
                          (metadata_tools.cumulative_support,
                           'create_cumulative_indexes')):
        monkeypatch.setattr(package, name,
                            lambda *a, _name=name, **k: calls.append((_name, a, k)))
    return calls


def _worker_data(**args: Any) -> types.SimpleNamespace:
    """Build the Worker context carrying a parsed-arguments namespace."""
    return types.SimpleNamespace(args=argparse.Namespace(**args))


#===============================================================================
# _IndexTask
#===============================================================================
def test_index_task_runs_one_volume_in_private_cache(
        engine_calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]]) -> None:
    """The index task rewrites both trees through a private cache and names its volume."""
    task = idx_worker._IndexTask('GO_0xxx', 'GO_0xxx_supplemental_index', 'C0*.LBL')
    data = _worker_data(volume_tree='gs://v', metadata_tree='gs://m', output_tree='/o')
    result = task('task-GO_0017', {'volume_id': 'GO_0017'}, data)
    assert result == (False, None)
    [cache] = _CacheStub.instances
    assert cache.kwargs == {'cache_name': None, 'delete_on_exit': True}
    assert cache.exited
    [(name, args, kwargs)] = engine_calls
    assert (name, args) == ('process_index', ('GO_0xxx_supplemental_index',))
    assert kwargs['glob'] == 'C0*.LBL'
    assert kwargs['volumes'] == ['GO_0017']
    assert kwargs['args'].volume_tree == 'cached:gs://v'
    assert kwargs['args'].metadata_tree == 'cached:gs://m'
    assert kwargs['args'].output_tree == '/o'
    # The Worker's own namespace is copied, never mutated.
    assert data.args.volume_tree == 'gs://v'


#===============================================================================
# _GeometryTask
#===============================================================================
def test_geometry_task_runs_one_volume_in_private_cache(
        engine_calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]]) -> None:
    """The geometry task rewrites metadata_tree and forwards globs and exclusions."""
    task = geom_worker._GeometryTask('GO_0xxx', 'GO_0xxx_supplemental_index',
                                     'C0*.LBL', '*_index.lbl', ['GO_0999'])
    data = _worker_data(metadata_tree='gs://m', output_tree='/o')
    result = task('task-GO_0017', {'volume_id': 'GO_0017'}, data)
    assert result == (False, None)
    [cache] = _CacheStub.instances
    assert cache.kwargs == {'cache_name': None, 'delete_on_exit': True}
    [(name, args, kwargs)] = engine_calls
    assert (name, args) == ('process_tables', ('GO_0xxx_supplemental_index',))
    assert kwargs['glob'] == 'C0*.LBL'
    assert kwargs['index_glob'] == '*_index.lbl'
    assert kwargs['exclude'] == ['GO_0999']
    assert kwargs['volumes'] == ['GO_0017']
    assert kwargs['args'].metadata_tree == 'cached:gs://m'
    assert kwargs['args'].output_tree == '/o'
    assert data.args.metadata_tree == 'gs://m'


#===============================================================================
# _CumulativeTask
#===============================================================================
def test_cumulative_task_runs_in_private_cache(
        engine_calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]]) -> None:
    """The cumulative task rewrites output_dir and forwards the exclusions."""
    task = cum_worker._CumulativeTask('GO_0xxx', 'GO_0xxx_supplemental_index',
                                      ['GO_0999'])
    data = _worker_data(output_dir='gs://o/GO_0xxx/GO_0999')
    result = task('cumulative', {}, data)
    assert result == (False, None)
    [cache] = _CacheStub.instances
    assert cache.kwargs == {'cache_name': None, 'delete_on_exit': True}
    [(name, args, kwargs)] = engine_calls
    assert (name, args) == ('create_cumulative_indexes', ('GO_0xxx_supplemental_index',))
    assert kwargs['exclude'] == ['GO_0999']
    assert kwargs['args'].output_dir == 'cached:gs://o/GO_0xxx/GO_0999'
    assert data.args.output_dir == 'gs://o/GO_0xxx/GO_0999'
