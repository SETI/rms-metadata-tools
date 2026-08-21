################################################################################
# tests/test_cli_host.py: Tests for metadata_tools.cli._host
################################################################################
"""Tests for pop_argv_flag, _strip_cloud_args, resolve_host_paths,
build_startup_script, volumes_as_task_file, and single_task_as_task_file."""
import argparse
import json
import sys
from pathlib import Path

import pytest

import metadata_tools.cli._host as _host_mod
from metadata_tools.cli._host import (
    _strip_cloud_args,
    build_startup_script,
    pop_argv_bool_flag,
    pop_argv_flag,
    resolve_host_paths,
    single_task_as_task_file,
    volumes_as_task_file,
)


def _simple_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument('volume_tree')
    return p


#===============================================================================
# pop_argv_flag
#===============================================================================

def test_pop_argv_flag_absent_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--other', 'val'])
    assert pop_argv_flag('--missing') is None
    assert sys.argv == ['cmd', '--other', 'val']


def test_pop_argv_flag_returns_value_and_strips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--flag', 'myvalue', '--other'])
    assert pop_argv_flag('--flag') == 'myvalue'
    assert sys.argv == ['cmd', '--other']


def test_pop_argv_flag_no_value_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--flag'])
    with pytest.raises(SystemExit):
        pop_argv_flag('--flag')


def test_pop_argv_flag_at_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--flag', 'v', 'positional'])
    assert pop_argv_flag('--flag') == 'v'
    assert sys.argv == ['cmd', 'positional']


#===============================================================================
# pop_argv_bool_flag
#===============================================================================

def test_pop_argv_bool_flag_absent_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--other'])
    assert pop_argv_bool_flag('--missing') is False
    assert sys.argv == ['cmd', '--other']


def test_pop_argv_bool_flag_present_returns_true_and_removes(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--flag', 'positional'])
    assert pop_argv_bool_flag('--flag') is True
    assert sys.argv == ['cmd', 'positional']


#===============================================================================
# _strip_cloud_args
#===============================================================================

def test_strip_cloud_args_empty_cloud_args_unchanged() -> None:
    argv = ['a', '--flag', 'val']
    assert _strip_cloud_args(argv, []) == argv


def test_strip_cloud_args_removes_flag_value_pair() -> None:
    argv = ['a', '--config', 'foo.yml', 'b']
    assert _strip_cloud_args(argv, ['--config', 'foo.yml']) == ['a', 'b']


def test_strip_cloud_args_removes_multiple_entries() -> None:
    argv = ['a', '--config', 'foo.yml', 'b', '--use-spot', 'c']
    assert _strip_cloud_args(argv, ['--config', 'foo.yml', '--use-spot']) == ['a', 'b', 'c']


def test_strip_cloud_args_preserves_remaining_order() -> None:
    argv = ['x', 'y', 'z']
    assert _strip_cloud_args(argv, ['y']) == ['x', 'z']


def test_strip_cloud_args_removes_first_occurrence_only() -> None:
    argv = ['--flag', 'a', 'other', '--flag', 'a']
    result = _strip_cloud_args(argv, ['--flag', 'a'])
    assert result == ['other', '--flag', 'a']


#===============================================================================
# resolve_host_paths
#===============================================================================

def test_resolve_host_paths_bare_config_uses_cloud_dir(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cloud_dir = tmp_path / 'cloud' / 'GO_0xxx'
    cloud_dir.mkdir(parents=True)
    host_dir = tmp_path / 'host'
    monkeypatch.setattr(sys, 'argv', ['cmd', '--config', 'gcp_index_config.yml'])
    resolve_host_paths(host_dir, cloud_dir)
    assert sys.argv[2] == str(cloud_dir / 'gcp_index_config.yml')


def test_resolve_host_paths_bare_task_file_uses_cloud_dir(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cloud_dir = tmp_path / 'cloud' / 'GO_0xxx'
    cloud_dir.mkdir(parents=True)
    host_dir = tmp_path / 'host'
    monkeypatch.setattr(sys, 'argv', ['cmd', '--task-file', 'tasks.json'])
    resolve_host_paths(host_dir, cloud_dir)
    assert sys.argv[2] == str(cloud_dir / 'tasks.json')


def test_resolve_host_paths_absolute_unchanged(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    host_dir = tmp_path / 'host'
    monkeypatch.setattr(sys, 'argv', ['cmd', '--config', '/absolute/path/cfg.yml'])
    resolve_host_paths(host_dir)
    assert sys.argv[2] == '/absolute/path/cfg.yml'


def test_resolve_host_paths_cloud_url_unchanged(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    host_dir = tmp_path / 'host'
    url = 'gs://my-bucket/config.yml'
    monkeypatch.setattr(sys, 'argv', ['cmd', '--config', url])
    resolve_host_paths(host_dir)
    assert sys.argv[2] == url


def test_resolve_host_paths_no_config_flag_is_noop(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    host_dir = tmp_path / 'host'
    monkeypatch.setattr(sys, 'argv', ['cmd', '--other', 'val'])
    resolve_host_paths(host_dir)
    assert sys.argv == ['cmd', '--other', 'val']


#===============================================================================
# build_startup_script
#===============================================================================

def test_build_startup_starts_with_shebang(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk')
    assert script.startswith('#!/bin/bash\n')


def test_build_startup_includes_oops_resources(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk')
    assert 'export OOPS_RESOURCES_DISK=my-disk' in script


def test_build_startup_oops_resources_from_env(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.setenv('OOPS_RESOURCES_DISK', 'env-disk')
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl))
    assert 'export OOPS_RESOURCES_DISK=env-disk' in script


def test_build_startup_missing_oops_resources_exits(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('OOPS_RESOURCES_DISK', raising=False)
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    with pytest.raises(SystemExit, match='--oops-resources'):
        build_startup_script('GO_0xxx', _simple_parser(), startup_template=str(tpl))


def test_build_startup_no_branch_line_in_pip_mode(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk')
    assert 'BRANCH' not in script


def test_build_startup_branch_from_arg(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  debug_branch='my-feature')
    assert 'export BRANCH=my-feature' in script


def test_build_startup_branch_from_env(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.setenv('GCP_DEBUG_BRANCH', 'env-branch')
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk')
    assert 'export BRANCH=env-branch' in script


def test_build_startup_branch_arg_overrides_env(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.setenv('GCP_DEBUG_BRANCH', 'env-branch')
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  debug_branch='cli-branch')
    assert 'export BRANCH=cli-branch' in script
    assert 'env-branch' not in script


def test_build_startup_template_from_env(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'custom.sh'
    tpl.write_text('custom content\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.setenv('GCP_STARTUP_TEMPLATE', str(tpl))
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(), oops_resources='my-disk')
    assert 'custom content' in script


def test_build_startup_empty_startup_template_env_uses_default(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Regression: GCP_STARTUP_TEMPLATE='' must not be passed to Path()."""
    cloud_dir = tmp_path / 'cloud' / 'GO_0xxx'
    cloud_dir.mkdir(parents=True)
    (tmp_path / 'cloud' / 'gcp_common_startup.sh').write_text('echo default\n')
    monkeypatch.setattr(_host_mod, 'cloud_dir_for', lambda _hid: cloud_dir)
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.setenv('GCP_STARTUP_TEMPLATE', '')
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(), oops_resources='my-disk')
    assert 'echo default' in script


def test_build_startup_template_arg_overrides_env(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl_arg = tmp_path / 'arg.sh'
    tpl_arg.write_text('from arg\n')
    tpl_env = tmp_path / 'env.sh'
    tpl_env.write_text('from env\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.setenv('GCP_STARTUP_TEMPLATE', str(tpl_env))
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl_arg), oops_resources='my-disk')
    assert 'from arg' in script
    assert 'from env' not in script


def test_build_startup_contains_worker_command(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  worker_cmd_name='metadata-index-worker',
                                  startup_template=str(tpl), oops_resources='my-disk')
    assert 'metadata-index-worker GO_0xxx' in script


def test_build_startup_contains_template_body(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('set -e\napt-get install python3\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk')
    assert 'set -e' in script
    assert 'apt-get install python3' in script


def test_build_startup_ssh_paste_exports_quota_project(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=True)
    assert 'GOOGLE_CLOUD_QUOTA_PROJECT' in script
    assert 'metadata.google.internal' in script


def test_build_startup_non_ssh_no_quota_project(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=False)
    assert 'GOOGLE_CLOUD_QUOTA_PROJECT' not in script


def test_build_startup_ssh_paste_replaces_cd_root(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('sudo apt-get install -y python3\ncd /root\npython3 -m venv venv\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=True)
    assert 'cd ~' in script
    assert 'cd /root' not in script
    assert 'SSH-pastable' in script


def test_build_startup_ssh_paste_false_keeps_cd_root(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('sudo apt-get install -y python3\ncd /root\npython3 -m venv venv\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=False)
    assert 'cd /root' in script
    assert 'cd ~' not in script
    assert 'SSH-pastable' not in script


def test_build_startup_ssh_paste_no_cd_root_is_noop(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=True)
    assert 'echo hello' in script
    assert 'cd ~' not in script
    assert 'cd /root' not in script


def test_build_startup_ssh_paste_set_plus_e_before_worker(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('set -e\necho setup\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  worker_cmd_name='metadata-index-worker',
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=True)
    # set +e must appear before the worker command so a worker failure cannot exit the shell
    set_plus_e_pos = script.index('set +e')
    worker_pos = script.index('metadata-index-worker')
    assert set_plus_e_pos < worker_pos


def test_build_startup_non_ssh_no_set_plus_e(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('set -e\necho setup\n')
    monkeypatch.setattr(sys, 'argv', ['cmd', 'gs://bucket/vol/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=False)
    assert 'set +e' not in script


def test_build_startup_ssh_paste_embeds_local_task_file(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo setup\n')
    tasks_file = tmp_path / 'tasks.json'
    tasks_file.write_text('[{"task_id": "t1", "data": {}}]')
    monkeypatch.setattr(sys, 'argv',
                        ['cmd', 'gs://bucket/vol/', '--task-file', str(tasks_file)])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  worker_cmd_name='metadata-index-worker',
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=True)
    assert 'task_id' in script          # task file content embedded
    assert '/tmp/tasks.json' in script   # worker references embedded file
    # worker command must come after the heredoc
    heredoc_end = script.index('EOF_TASKS')
    worker_pos = script.index('metadata-index-worker')
    assert heredoc_end < worker_pos


def test_build_startup_ssh_paste_remote_task_file_passed_through(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo setup\n')
    monkeypatch.setattr(sys, 'argv',
                        ['cmd', 'gs://bucket/vol/', '--task-file', 'gs://bucket/tasks.json'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  worker_cmd_name='metadata-index-worker',
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=True)
    assert 'gs://bucket/tasks.json' in script
    assert 'EOF_TASKS' not in script     # no heredoc for remote URL


def test_build_startup_non_ssh_task_file_not_included(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo setup\n')
    tasks_file = tmp_path / 'tasks.json'
    tasks_file.write_text('[{"task_id": "t1", "data": {}}]')
    monkeypatch.setattr(sys, 'argv',
                        ['cmd', 'gs://bucket/vol/', '--task-file', str(tasks_file)])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk',
                                  for_ssh=False)
    assert 'task_id' not in script       # task file NOT embedded in non-SSH mode
    assert '/tmp/tasks.json' not in script


def test_build_startup_expands_env_vars_in_argv(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """$VAR references in argv are expanded via os.environ (which includes .env values)."""
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    monkeypatch.setenv('RMS_VOLUMES_GCP', 'gs://my-bucket/volumes')
    monkeypatch.setattr(sys, 'argv', ['cmd', '$RMS_VOLUMES_GCP/GO_0xxx/'])
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
    script = build_startup_script('GO_0xxx', _simple_parser(),
                                  startup_template=str(tpl), oops_resources='my-disk')
    assert 'gs://my-bucket/volumes/GO_0xxx/' in script
    assert '$RMS_VOLUMES_GCP' not in script


#===============================================================================
# volumes_as_task_file
#===============================================================================

def test_volumes_as_task_file_noop_without_volumes(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--config', 'cfg.yml'])
    original = list(sys.argv)
    with volumes_as_task_file():
        assert sys.argv == original


def test_volumes_as_task_file_noop_without_config(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--volumes', 'GO_0001'])
    original = list(sys.argv)
    with volumes_as_task_file():
        assert sys.argv == original


def test_volumes_as_task_file_rewrites_argv_inside_block(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv',
                        ['cmd', '--config', 'cfg.yml', '--volumes', 'GO_0001', 'GO_0002'])
    with volumes_as_task_file():
        assert '--volumes' not in sys.argv
        assert '--task-file' in sys.argv
        tf_idx = sys.argv.index('--task-file')
        data = json.loads(Path(sys.argv[tf_idx + 1]).read_text())
        vols = [t['data']['volume_id'] for t in data]
        assert vols == ['GO_0001', 'GO_0002']


def test_volumes_as_task_file_volumes_absent_from_argv_inside(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv',
                        ['cmd', '--config', 'cfg.yml', '--volumes', 'GO_0001'])
    with volumes_as_task_file():
        assert 'GO_0001' not in sys.argv
        assert '--config' in sys.argv


#===============================================================================
# single_task_as_task_file
#===============================================================================

def test_single_task_as_task_file_noop_when_task_file_present(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tf = tmp_path / 'tasks.json'
    tf.write_text('[]')
    monkeypatch.setattr(sys, 'argv', ['cmd', '--task-file', str(tf)])
    original = list(sys.argv)
    with single_task_as_task_file():
        assert sys.argv == original


def test_single_task_as_task_file_injects_task_file(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd'])
    with single_task_as_task_file():
        assert '--task-file' in sys.argv
        tf_idx = sys.argv.index('--task-file')
        data = json.loads(Path(sys.argv[tf_idx + 1]).read_text())
        assert len(data) == 1
        assert data[0]['task_id'] == 'cumulative'


def test_single_task_as_task_file_task_has_empty_data(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd'])
    with single_task_as_task_file():
        tf_idx = sys.argv.index('--task-file')
        data = json.loads(Path(sys.argv[tf_idx + 1]).read_text())
        assert data[0]['data'] == {}
################################################################################
