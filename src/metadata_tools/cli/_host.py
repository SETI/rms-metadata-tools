"""Shared host-directory injection for CLI entry points."""
import argparse
import asyncio
import contextlib
import os
import shlex
import subprocess  # nosec B404 - launches the trusted sibling cloud_tasks console script
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def load_host(host_id: str) -> Path:
    """Validate the host directory exists and remove HOST_ID from sys.argv.

    Resolves hosts/<host_id>/ relative to the installed package, validates it
    exists, and drops HOST_ID from sys.argv so the support module's argparser
    sees the normal positional arguments it expects. Callers should also call
    ``metadata_tools.config.set_host(host_id)`` to register that host's config
    modules (see issue #112).

    Returns:
        Absolute path to the resolved host directory.
    """
    host_dir = Path(__file__).parent.parent / 'hosts' / host_id
    if not host_dir.is_dir():
        sys.exit(f'Unknown host: {host_id!r} — no directory at {host_dir}')
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    return host_dir


def host_dir_for(host_id: str) -> Path:
    """Return the absolute host directory path without modifying sys.argv or sys.path.

    Useful for resolving the path in a shell script, e.g.::

        host_dir=$(python -c "
            from metadata_tools.cli._host import host_dir_for
            print(host_dir_for('GO_0xxx'))")
    """
    return Path(__file__).parent.parent / 'hosts' / host_id


def cloud_dir_for(host_id: str) -> Path:
    """Return the absolute cloud deployment directory path for *host_id*.

    Resolves ``cloud/<host_id>/`` relative to the repository root (four levels
    above this file in an editable install).  Only valid in a development checkout;
    a regular ``pip install`` lands this file in site-packages where the ``cloud/``
    tree is not present.
    """
    return Path(__file__).parent.parent.parent.parent / 'cloud' / host_id


def resolve_host_paths(host_dir: Path, cloud_dir: Path | None = None) -> None:
    """Rewrite relative ``--config`` and ``--task-file`` values in sys.argv to absolute paths.

    For either ``--config`` or ``--task-file``:

    * **Bare filenames** (no directory components) are resolved against *cloud_dir* (if
      provided) or *host_dir*.
    * **Relative paths with directory components** that do not exist from the current working
      directory are resolved against the repository root (two levels above *cloud_dir*), so
      paths like ``cloud/GO_0xxx/gcp_cumulative_config.yml`` work regardless of cwd.

    Absolute paths and cloud URLs (``gs://``, ``s3://``, ``https://``, etc.) are left
    unchanged.
    """
    base = cloud_dir if cloud_dir is not None else host_dir
    for i, arg in enumerate(sys.argv[:-1]):
        if arg in {'--config', '--task-file'}:
            value = sys.argv[i + 1]
            p = Path(value)
            if p.is_absolute() or '://' in value:
                continue
            if p.parent == Path('.'):
                # Bare filename: always resolve against base (cloud dir or host dir).
                sys.argv[i + 1] = str(base / value)
            elif not p.exists() and cloud_dir is not None:
                # Relative path with directory components not found from cwd:
                # try from the repository root (two levels above cloud_dir).
                candidate = cloud_dir.parent.parent / value
                if candidate.exists():
                    sys.argv[i + 1] = str(candidate)


def resolve_task_file(host_dir: Path) -> None:
    """Alias for :func:`resolve_host_paths`; kept for backwards compatibility."""
    resolve_host_paths(host_dir)


def pop_argv_flag(flag: str) -> str | None:
    """Remove *flag* and its value from sys.argv and return the value.

    Returns ``None`` if *flag* is absent.  Calls ``sys.exit`` with an error
    message if *flag* is present but has no following value.
    """
    if flag not in sys.argv:
        return None
    idx = sys.argv.index(flag)
    if idx + 1 >= len(sys.argv):
        sys.exit(f'{flag} requires a value')
    value = sys.argv[idx + 1]
    del sys.argv[idx:idx + 2]
    return value


def _strip_cloud_args(argv: list[str], cloud_args: list[str]) -> list[str]:
    """Remove cloud_args elements from argv in order, returning what remains.

    Walks both lists in tandem, consuming each cloud_args element the first time
    it appears in argv.  This correctly handles flag+value pairs (e.g.
    ``['--config', 'foo.yml']``) because argparse returns them as consecutive
    entries in the extras list and they appear consecutively in argv too.
    """
    cloud_iter = iter(cloud_args)
    next_drop = next(cloud_iter, None)
    remaining = []
    for arg in argv:
        if arg == next_drop:
            next_drop = next(cloud_iter, None)
        else:
            remaining.append(arg)
    return remaining


def build_startup_script(host_id: str, parser: argparse.ArgumentParser,
                         worker_cmd_name: str | None = None,
                         startup_template: str | Path | None = None,
                         oops_resources: str | None = None,
                         debug_branch: str | None = None) -> str:
    """Build and return the GCP instance startup script as a string.

    Combines the startup template with a worker command reconstructed from the
    metadata_tools arguments in ``sys.argv`` (unknown flags, including any
    cloud_tasks or ``--create-startup-file`` flags, are stripped).  The git
    branch to clone is injected as ``BRANCH``.

    Args:
        host_id: The host identifier (e.g. ``'GO_0xxx'``).
        parser: The argparser for this command; used to separate metadata_tools
            flags from everything else.
        worker_cmd_name: Name of the worker console script to embed. Defaults to
            the name of the current executable.
        startup_template: Path to the startup template file to use instead of the
            default ``cloud/gcp_common_startup.sh``.  Falls back to the
            ``GCP_STARTUP_TEMPLATE`` environment variable when ``None``.
        oops_resources: Name of the persistent disk to mount as OOPS resources,
            injected as ``OOPS_RESOURCES_DISK`` in the script header.  Falls back
            to the ``OOPS_RESOURCES_DISK`` environment variable when ``None``.
            Calls ``sys.exit`` if neither is provided.
        debug_branch: Git branch to clone on the GCP VM, injected as ``BRANCH``
            in the script header.  Falls back to the ``GCP_DEBUG_BRANCH``
            environment variable.  When neither is set the startup template
            installs from PyPI instead of cloning the repository.

    Returns:
        The complete startup script text.
    """
    _ns, extra_args = parser.parse_known_args(sys.argv[1:])
    worker_argv = _strip_cloud_args(sys.argv[1:], extra_args)

    cmd_name = worker_cmd_name if worker_cmd_name is not None else Path(sys.argv[0]).name
    worker_cmd = shlex.join([cmd_name, host_id] + worker_argv)

    resolved_branch = debug_branch or os.environ.get('GCP_DEBUG_BRANCH')

    resolved_template = startup_template or os.environ.get('GCP_STARTUP_TEMPLATE')
    template_path = (Path(resolved_template) if resolved_template
                     else cloud_dir_for(host_id).parent / 'gcp_common_startup.sh')

    resolved_oops = oops_resources or os.environ.get('OOPS_RESOURCES_DISK')
    if not resolved_oops:
        sys.exit('--oops-resources or $OOPS_RESOURCES_DISK is required')
    header_lines = []
    if resolved_branch:
        header_lines.append(f'export BRANCH={shlex.quote(resolved_branch)}')
    header_lines.append(f'export OOPS_RESOURCES_DISK={shlex.quote(resolved_oops)}')
    header = '\n'.join(header_lines)
    return f'#!/bin/bash\n{header}\n{template_path.read_text(encoding="utf-8").rstrip()}\n\n{worker_cmd}\n'


def dispatch_cloud_run_if_config(host_id: str,
                                 parser: argparse.ArgumentParser,
                                 worker_cmd_name: str | None = None,
                                 startup_template: str | Path | None = None,
                                 oops_resources: str | None = None,
                                 service_account: str | None = None,
                                 debug_branch: str | None = None) -> int | None:
    """Shell out to ``cloud_tasks run`` if ``--config`` is present in sys.argv.

    Must be called after :func:`load_host` and :func:`resolve_host_paths` so that
    bare ``--config`` and ``--task-file`` filenames have already been resolved to
    absolute paths under the host directory.

    Generates the GCP instance startup script at runtime by combining the startup
    template with a worker command reconstructed from the metadata_tools arguments
    in ``sys.argv``.  The current git branch is detected and injected as ``BRANCH``
    so the VM clones the same code that dispatched it.

    The startup script is delivered to cloud_tasks by injecting ``startup_script_file``
    into a modified copy of the config YAML (written to a temp file) because
    cloud_tasks reads the startup script from the YAML, not from a CLI flag.

    If ``--config`` is absent, returns ``None`` and the caller continues with
    normal local Worker execution.  If ``--config`` is present, invokes::

        cloud_tasks run <cloud_tasks_args (with --config replaced by temp YAML)>

    as a subprocess, waits for it to finish (including after Ctrl+C), and returns
    its exit code for the caller to pass to ``sys.exit()``.

    If the ``GCP_SERVICE_ACCOUNT`` environment variable is set and
    ``--service-account`` is not already in the cloud_tasks args, it is appended
    automatically.

    Args:
        host_id: The host identifier (e.g. ``'GO_0xxx'``).
        parser: The argparser for this command; used to separate metadata_tools
            flags (kept in the startup script worker command) from cloud_tasks
            flags (passed to ``cloud_tasks run``).
        worker_cmd_name: Name of the worker console script to embed in the GCP
            startup script (e.g. ``'metadata-index-worker'``).  Defaults to the
            name of the current executable (``Path(sys.argv[0]).name``), which
            is appropriate when the dispatcher and worker share the same entry
            point name.
        startup_template: Path to the startup template file passed to
            :func:`build_startup_script`; see that function for details.
        oops_resources: Persistent disk name passed to :func:`build_startup_script`;
            see that function for details.
        service_account: GCP service account to pass to ``cloud_tasks run`` via
            ``--service-account``.  Takes precedence over the ``GCP_SERVICE_ACCOUNT``
            environment variable.
        debug_branch: Git branch passed to :func:`build_startup_script`; see that
            function for details.
    """
    if '--config' not in sys.argv:
        return None

    # Split argv into metadata_tools args (→ startup script) and cloud_tasks args (→ dispatch).
    _ns, cloud_args = parser.parse_known_args(sys.argv[1:])

    startup = build_startup_script(host_id, parser, worker_cmd_name, startup_template,
                                   oops_resources, debug_branch)

    # Write startup script to a temp file; must outlive the subprocess.
    with tempfile.NamedTemporaryFile(suffix='.sh', delete=False, mode='w') as sh_tmp:
        sh_tmp.write(startup)
        sh_tmp_name = sh_tmp.name
    # sh_tmp is closed (but not deleted); clean up in the outer finally.
    try:
        # cloud_tasks reads the startup script from startup_script_file in the config
        # YAML — passing --startup-script-file on the CLI has no effect.  Inject the
        # field into a modified copy of the config YAML and swap the --config path.
        import yaml  # only needed on the GCP dispatch path (cloud extra)

        config_path_idx = next(i for i, a in enumerate(cloud_args) if a == '--config')
        config_path = cloud_args[config_path_idx + 1]
        with open(config_path, encoding='utf-8') as cfg_f:
            config_data: dict[str, object] = yaml.safe_load(cfg_f)

        provider = str(config_data.get('provider', 'gcp')).lower()
        provider_section = config_data.setdefault(provider, {})
        if not isinstance(provider_section, dict):
            raise TypeError(f'Config YAML section {provider!r} is not a mapping')
        provider_section['startup_script_file'] = sh_tmp_name

        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False, mode='w') as cfg_tmp:
            yaml.dump(config_data, cfg_tmp, default_flow_style=False)
            cfg_tmp_name = cfg_tmp.name
        try:
            modified_cloud_args = list(cloud_args)
            modified_cloud_args[config_path_idx + 1] = cfg_tmp_name

            extra: list[str] = []
            sa = service_account or os.environ.get('GCP_SERVICE_ACCOUNT')
            if sa and '--service-account' not in cloud_args:
                extra += ['--service-account', sa]

            cloud_tasks_bin = Path(sys.executable).parent / 'cloud_tasks'
            # shell=False (the default); executable and args come from this process only.
            proc = subprocess.Popen(  # nosec B603
                [str(cloud_tasks_bin), 'run'] + modified_cloud_args + extra
            )
            try:
                proc.wait()
            except KeyboardInterrupt:
                proc.wait()  # subprocess already got SIGINT; let it finish cleanup
            return proc.returncode
        finally:
            os.unlink(cfg_tmp_name)
    finally:
        os.unlink(sh_tmp_name)


@contextlib.contextmanager
def single_task_as_task_file() -> Iterator[None]:
    """Context manager: inject a single-task file when ``--task-file`` is absent.

    Cumulative runs always consist of exactly one task.  When ``--task-file`` is
    not already in sys.argv, write a minimal one-task JSON to a temp file and
    add ``--task-file <path>`` to sys.argv so the Worker has a task source.
    The temp file is deleted automatically when the ``with`` block exits.
    """
    if '--task-file' in sys.argv:
        yield
        return
    import json
    task = [{'task_id': 'cumulative', 'data': {}}]
    with tempfile.NamedTemporaryFile(suffix='.json', delete=True, mode='w') as tmp:
        tmp.write(json.dumps(task))
        tmp.flush()
        sys.argv += ['--task-file', tmp.name]
        yield


@contextlib.contextmanager
def volumes_as_task_file() -> Iterator[None]:
    """Context manager: convert ``--volumes`` to a temp task file when ``--config`` is also present.

    ``cloud_tasks run`` does not understand ``--volumes``.  When both flags are
    present (GCP dispatch with an inline volume list), materialise the volumes
    into a temporary JSON task file, rewrite sys.argv to use ``--task-file``
    instead, and drop the ``--volumes`` entries so dispatch proceeds normally.
    The temp file is deleted automatically when the ``with`` block exits, even
    on interrupt.
    """
    if '--volumes' not in sys.argv or '--config' not in sys.argv:
        yield
        return
    from metadata_tools import task_list_support as tl
    idx = sys.argv.index('--volumes')
    vols = [v for v in sys.argv[idx + 1:] if not v.startswith('-')]
    with tempfile.NamedTemporaryFile(suffix='.json', delete=True, mode='w') as tmp:
        tl.write_task_file(vols, tmp.name)
        sys.argv = [a for a in sys.argv if a not in (['--volumes'] + vols)]
        sys.argv += ['--task-file', tmp.name]
        yield


def run_cloud_worker(
    parser: argparse.ArgumentParser,
    task: Any,
    *,
    supports_volumes: bool = True,
) -> None:
    """Run an async cloud Worker with the given task callable.

    Handles pre-parsing ``sys.argv`` for ``--volumes`` to build a task source
    iterator, then constructs and starts a ``cloud_tasks.worker.Worker``.

    Parameters:
        parser: The argparser for the command (passed through to Worker).
        task: Picklable callable to execute per task (index, geometry, or cumulative).
        supports_volumes: When False, skip the ``--volumes`` pre-parse step
            (cumulative tasks do not accept per-volume task sources).
    """
    from cloud_tasks.worker import Worker

    async def _run() -> None:
        task_src: Any = None
        if supports_volumes:
            pre_args, _ = parser.parse_known_args(sys.argv[1:])
            if pre_args.volumes:
                from metadata_tools import task_list_support as tl
                tasks = list(tl.task_generator(pre_args.volumes))

                def task_src() -> Iterator[dict[str, Any]]:
                    return iter(tasks)

        worker = Worker(task, task_source=task_src, args=sys.argv[1:], argparser=parser)
        await worker.start()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        sys.exit(130)
