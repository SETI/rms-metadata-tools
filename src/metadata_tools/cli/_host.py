"""Shared host-directory injection for CLI entry points."""
import subprocess
import sys
from pathlib import Path


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

    Useful for shell one-liners that just need the path, e.g.::

        host_dir=$(python -c "from metadata_tools.cli._host import host_dir_for; print(host_dir_for('GO_0xxx'))")
    """
    return Path(__file__).parent.parent / 'hosts' / host_id


def resolve_host_paths(host_dir: Path) -> None:
    """Rewrite bare ``--config`` and ``--task-file`` values in sys.argv to absolute paths.

    If the user passes a bare filename (no directory components, not absolute, not a URL)
    for either ``--config`` or ``--task-file``, it is resolved against *host_dir* so the
    CLI can be invoked from any working directory.  Absolute paths, paths with directory
    separators, and cloud URLs (``gs://``, ``s3://``, ``https://``, etc.) are left
    unchanged.
    """
    for i, arg in enumerate(sys.argv[:-1]):
        if arg in {'--config', '--task-file'}:
            value = sys.argv[i + 1]
            p = Path(value)
            if not p.is_absolute() and '://' not in value and p.parent == Path('.'):
                sys.argv[i + 1] = str(host_dir / value)


def resolve_task_file(host_dir: Path) -> None:
    """Alias for :func:`resolve_host_paths`; kept for backwards compatibility."""
    resolve_host_paths(host_dir)


def dispatch_cloud_run_if_config() -> None:
    """Shell out to ``cloud_tasks run`` if ``--config`` is present in sys.argv.

    Must be called after :func:`load_host` and :func:`resolve_host_paths` so that
    bare ``--config`` and ``--task-file`` filenames have already been resolved to
    absolute paths under the host directory.

    If ``--config`` is absent, returns immediately and the caller continues with
    normal local Worker execution.  If ``--config`` is present, invokes::

        cloud_tasks run <sys.argv[1:]>

    as a subprocess and exits with its return code — the function never returns
    in that case.
    """
    if '--config' not in sys.argv:
        return
    sys.exit(subprocess.run(['cloud_tasks', 'run'] + sys.argv[1:]).returncode)
