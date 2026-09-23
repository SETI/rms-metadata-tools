################################################################################
# tests/test_cli_dispatch.py: GCP dispatch and cloud Worker startup in cli._host
################################################################################
"""Tests for dispatch_cloud_run_if_config and run_cloud_worker.

Both run only on the cloud paths, so these tests stand in for a GCP run: the
``cloud_tasks run`` subprocess is replaced by a recorder, and the cloud_tasks
Worker by a stub.
"""
import argparse
import os
import subprocess
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import pytest
import yaml

import metadata_tools.cli._host as _host_mod
from metadata_tools.cli._host import dispatch_cloud_run_if_config, run_cloud_worker

STARTUP = '#!/bin/bash\necho startup\n'


def _parser() -> argparse.ArgumentParser:
    """Return a parser with one positional tree and a --volumes option."""
    p = argparse.ArgumentParser()
    p.add_argument('volume_tree')
    p.add_argument('--volumes', nargs='*')
    return p


class _PopenRecorder:
    """Stand-in for subprocess.Popen that records what dispatch hands it.

    The temp YAML and startup script exist only while the subprocess runs, so
    their contents are captured at construction.
    """

    calls: ClassVar[list['_PopenRecorder']] = []
    returncode_to_use: ClassVar[int] = 0

    def __init__(self, argv: list[str]) -> None:
        self.argv = argv
        cfg_path = argv[argv.index('--config') + 1]
        self.config_path = cfg_path
        with open(cfg_path, encoding='utf-8') as f:
            self.config: dict[str, Any] = yaml.safe_load(f)
        self.startup_path = self.config['gcp']['startup_script_file']
        with open(self.startup_path, encoding='utf-8') as f:
            self.startup = f.read()
        self.returncode = _PopenRecorder.returncode_to_use
        _PopenRecorder.calls.append(self)

    def wait(self) -> int:
        return self.returncode


@pytest.fixture
def dispatch_env(monkeypatch: pytest.MonkeyPatch,
                 tmp_path: Path) -> Callable[..., Path]:
    """Arrange a dispatch: a config YAML, a stubbed startup script and Popen.

    Returns:
        A factory taking the config mapping to write (and optional extra argv)
        that sets sys.argv and returns the config path.
    """
    _PopenRecorder.calls = []
    _PopenRecorder.returncode_to_use = 0
    monkeypatch.setattr(subprocess, 'Popen', _PopenRecorder)
    monkeypatch.setattr(_host_mod, 'build_startup_script', lambda *a, **k: STARTUP)
    monkeypatch.delenv('GCP_SERVICE_ACCOUNT', raising=False)

    def _make(config: Any, *extra: str) -> Path:
        cfg = tmp_path / 'gcp_config.yml'
        cfg.write_text(yaml.dump(config), encoding='utf-8')
        monkeypatch.setattr(sys, 'argv',
                            ['metadata-index-cloud', '/vols', '--config', str(cfg), *extra])
        return cfg

    return _make


#===============================================================================
# dispatch_cloud_run_if_config
#===============================================================================
def test_dispatch_without_config_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no --config in argv, dispatch declines and the caller runs locally."""
    monkeypatch.setattr(sys, 'argv', ['metadata-index-cloud', '/vols'])
    assert dispatch_cloud_run_if_config('GO_0xxx', _parser()) is None


def test_dispatch_runs_cloud_tasks_with_injected_startup(
        dispatch_env: Callable[..., Path]) -> None:
    """The subprocess gets `cloud_tasks run` and a temp YAML naming the startup script."""
    cfg = dispatch_env({'provider': 'GCP', 'gcp': {'zone': 'us-central1-a'}})
    assert dispatch_cloud_run_if_config('GO_0xxx', _parser()) == 0
    [call] = _PopenRecorder.calls
    assert call.argv[0] == str(Path(sys.executable).parent / 'cloud_tasks')
    assert call.argv[1:] == ['run', '--config', call.config_path]
    assert call.config_path != str(cfg)
    assert call.config['gcp']['zone'] == 'us-central1-a'
    assert call.startup == STARTUP


def test_dispatch_defaults_provider_section_to_gcp(
        dispatch_env: Callable[..., Path]) -> None:
    """A config without a provider key gets its startup script under 'gcp'."""
    dispatch_env({'run': {'max_instances': 2}})
    dispatch_cloud_run_if_config('GO_0xxx', _parser())
    [call] = _PopenRecorder.calls
    assert call.config['run'] == {'max_instances': 2}
    assert set(call.config['gcp']) == {'startup_script_file'}


def test_dispatch_removes_temp_files(dispatch_env: Callable[..., Path]) -> None:
    """Both the temp YAML and the temp startup script are deleted afterward."""
    dispatch_env({'gcp': {}})
    dispatch_cloud_run_if_config('GO_0xxx', _parser())
    [call] = _PopenRecorder.calls
    assert not os.path.exists(call.config_path)
    assert not os.path.exists(call.startup_path)


def test_dispatch_returns_subprocess_exit_code(dispatch_env: Callable[..., Path]) -> None:
    """The cloud_tasks exit code is returned for the caller to pass to sys.exit."""
    dispatch_env({'gcp': {}})
    _PopenRecorder.returncode_to_use = 3
    assert dispatch_cloud_run_if_config('GO_0xxx', _parser()) == 3


def test_dispatch_rejects_non_mapping_provider_section(
        dispatch_env: Callable[..., Path]) -> None:
    """A provider section that is not a mapping is a TypeError, and nothing runs."""
    dispatch_env({'provider': 'gcp', 'gcp': 'oops'})
    with pytest.raises(TypeError, match="section 'gcp' is not a mapping"):
        dispatch_cloud_run_if_config('GO_0xxx', _parser())
    assert _PopenRecorder.calls == []


def test_dispatch_rejects_flag_like_config_value(
        monkeypatch: pytest.MonkeyPatch, dispatch_env: Callable[..., Path]) -> None:
    """A --config value starting with '-' exits with an explanatory message."""
    dispatch_env({'gcp': {}})
    # --config followed directly by another flag leaves that flag as its value.
    monkeypatch.setattr(sys, 'argv',
                        ['metadata-index-cloud', '/vols', '--config', '--dry-run'])
    with pytest.raises(SystemExit, match='--config value looks like a flag'):
        dispatch_cloud_run_if_config('GO_0xxx', _parser())


def test_dispatch_appends_service_account_from_env(
        monkeypatch: pytest.MonkeyPatch, dispatch_env: Callable[..., Path]) -> None:
    """GCP_SERVICE_ACCOUNT is passed as --service-account when not given on the CLI."""
    dispatch_env({'gcp': {}})
    monkeypatch.setenv('GCP_SERVICE_ACCOUNT', 'sa@example.iam.gserviceaccount.com')
    dispatch_cloud_run_if_config('GO_0xxx', _parser())
    [call] = _PopenRecorder.calls
    assert call.argv[-2:] == ['--service-account', 'sa@example.iam.gserviceaccount.com']


def test_dispatch_service_account_argument_beats_env(
        monkeypatch: pytest.MonkeyPatch, dispatch_env: Callable[..., Path]) -> None:
    """The service_account parameter takes precedence over GCP_SERVICE_ACCOUNT."""
    dispatch_env({'gcp': {}})
    monkeypatch.setenv('GCP_SERVICE_ACCOUNT', 'env@example.iam.gserviceaccount.com')
    dispatch_cloud_run_if_config('GO_0xxx', _parser(),
                                 service_account='arg@example.iam.gserviceaccount.com')
    [call] = _PopenRecorder.calls
    assert call.argv[-2:] == ['--service-account', 'arg@example.iam.gserviceaccount.com']


def test_dispatch_keeps_explicit_service_account_flag(
        monkeypatch: pytest.MonkeyPatch, dispatch_env: Callable[..., Path]) -> None:
    """An explicit --service-account on the CLI is not duplicated from the env."""
    dispatch_env({'gcp': {}}, '--service-account', 'cli@example.iam.gserviceaccount.com')
    monkeypatch.setenv('GCP_SERVICE_ACCOUNT', 'env@example.iam.gserviceaccount.com')
    dispatch_cloud_run_if_config('GO_0xxx', _parser())
    [call] = _PopenRecorder.calls
    assert call.argv.count('--service-account') == 1
    assert call.argv[-1] == 'cli@example.iam.gserviceaccount.com'


#===============================================================================
# run_cloud_worker
#===============================================================================
class _WorkerStub:
    """Stand-in for cloud_tasks.worker.Worker recording its construction."""

    instances: ClassVar[list['_WorkerStub']] = []
    raise_on_start: ClassVar[BaseException | None] = None

    def __init__(self, task: Any, *, task_source: Any, args: list[str],
                 argparser: argparse.ArgumentParser) -> None:
        self.task = task
        self.task_source = task_source
        self.args = args
        self.argparser = argparser
        _WorkerStub.instances.append(self)

    async def start(self) -> None:
        if _WorkerStub.raise_on_start is not None:
            raise _WorkerStub.raise_on_start


@pytest.fixture
def worker_stub(monkeypatch: pytest.MonkeyPatch) -> type[_WorkerStub]:
    """Install _WorkerStub as cloud_tasks.worker.Worker for the test."""
    _WorkerStub.instances = []
    _WorkerStub.raise_on_start = None
    module = types.ModuleType('cloud_tasks.worker')
    module.Worker = _WorkerStub  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, 'cloud_tasks.worker', module)
    return _WorkerStub


def test_run_cloud_worker_builds_task_source_from_volumes(
        monkeypatch: pytest.MonkeyPatch, worker_stub: type[_WorkerStub]) -> None:
    """--volumes becomes a task source yielding one task per volume."""
    monkeypatch.setattr(sys, 'argv',
                        ['metadata-index-worker', '/vols', '--volumes', 'GO_0001', 'GO_0002'])
    task = object()
    run_cloud_worker(_parser(), task)
    [worker] = worker_stub.instances
    assert worker.task is task
    assert worker.args == ['/vols', '--volumes', 'GO_0001', 'GO_0002']
    assert list(worker.task_source()) == [
        {'task_id': 'task-GO_0001', 'data': {'volume_id': 'GO_0001'}},
        {'task_id': 'task-GO_0002', 'data': {'volume_id': 'GO_0002'}},
    ]


def test_run_cloud_worker_without_volumes_has_no_task_source(
        monkeypatch: pytest.MonkeyPatch, worker_stub: type[_WorkerStub]) -> None:
    """With no --volumes the Worker takes its tasks from its own arguments."""
    monkeypatch.setattr(sys, 'argv', ['metadata-index-worker', '/vols'])
    run_cloud_worker(_parser(), object())
    [worker] = worker_stub.instances
    assert worker.task_source is None


def test_run_cloud_worker_skips_volumes_when_unsupported(
        monkeypatch: pytest.MonkeyPatch, worker_stub: type[_WorkerStub]) -> None:
    """supports_volumes=False ignores --volumes (cumulative runs are one task)."""
    monkeypatch.setattr(sys, 'argv',
                        ['metadata-cumulative-worker', '/vols', '--volumes', 'GO_0001'])
    run_cloud_worker(_parser(), object(), supports_volumes=False)
    [worker] = worker_stub.instances
    assert worker.task_source is None


def test_run_cloud_worker_ctrl_c_exits_130(
        monkeypatch: pytest.MonkeyPatch, worker_stub: type[_WorkerStub]) -> None:
    """A KeyboardInterrupt from the Worker exits with the conventional status 130."""
    monkeypatch.setattr(sys, 'argv', ['metadata-index-worker', '/vols'])
    worker_stub.raise_on_start = KeyboardInterrupt()
    with pytest.raises(SystemExit) as excinfo:
        run_cloud_worker(_parser(), object())
    assert excinfo.value.code == 130
