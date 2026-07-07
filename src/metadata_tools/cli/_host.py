"""Shared host-directory injection for CLI entry points."""
import argparse
import asyncio
import contextlib
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def load_host(host_id: str) -> Path:
    """Inject the host directory into sys.path and remove HOST_ID from sys.argv.

    Resolves hosts/<host_id>/ relative to the installed package, validates it
    exists, prepends it to sys.path (so bare ``import host_config`` etc. resolve),
    and drops HOST_ID from sys.argv so the support module's argparser sees the
    normal positional arguments it expects.

    Returns:
        Absolute path to the resolved host directory.
    """
    host_dir = Path(__file__).parent.parent / 'hosts' / host_id
    if not host_dir.is_dir():
        sys.exit(f'Unknown host: {host_id!r} — no directory at {host_dir}')
    sys.path.insert(0, str(host_dir))
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
    """Rewrite bare ``--config`` and ``--task-file`` values in sys.argv to absolute paths.

    If the user passes a bare filename (no directory components, not absolute, not a URL)
    for either ``--config`` or ``--task-file``, it is resolved against *cloud_dir* (if
    provided) or *host_dir* so the CLI can be invoked from any working directory.
    Absolute paths, paths with directory separators, and cloud URLs (``gs://``,
    ``s3://``, ``https://``, etc.) are left unchanged.
    """
    base = cloud_dir if cloud_dir is not None else host_dir
    for i, arg in enumerate(sys.argv[:-1]):
        if arg in {'--config', '--task-file'}:
            value = sys.argv[i + 1]
            p = Path(value)
            if not p.is_absolute() and '://' not in value and p.parent == Path('.'):
                sys.argv[i + 1] = str(base / value)


def resolve_task_file(host_dir: Path) -> None:
    """Alias for :func:`resolve_host_paths`; kept for backwards compatibility."""
    resolve_host_paths(host_dir)


def dispatch_cloud_run_if_config() -> int | None:
    """Shell out to ``cloud_tasks run`` if ``--config`` is present in sys.argv.

    Must be called after :func:`load_host` and :func:`resolve_host_paths` so that
    bare ``--config`` and ``--task-file`` filenames have already been resolved to
    absolute paths under the host directory.

    If ``--config`` is absent, returns ``None`` and the caller continues with
    normal local Worker execution.  If ``--config`` is present, invokes::

        cloud_tasks run <sys.argv[1:]>

    as a subprocess, waits for it to finish (including after Ctrl+C), and returns
    its exit code for the caller to pass to ``sys.exit()``.
    """
    if '--config' not in sys.argv:
        return None
    cloud_tasks_bin = Path(sys.executable).parent / 'cloud_tasks'
    proc = subprocess.Popen([str(cloud_tasks_bin), 'run'] + sys.argv[1:])
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.wait()  # subprocess already got SIGINT; let it finish its own cleanup
    return proc.returncode


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

    Args:
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
