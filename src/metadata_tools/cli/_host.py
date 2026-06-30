"""Shared host-directory injection for CLI entry points."""
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


def resolve_task_file(host_dir: Path) -> None:
    """Rewrite a relative --task-file value in sys.argv to an absolute path under host_dir.

    If the user passes ``--task-file some_name.json`` (a relative path, not an absolute
    path and not a URL), the bare name is resolved against the host directory so that the
    CLI can be invoked from any working directory, not just the host directory itself.
    Absolute paths and cloud URLs (``gs://``, ``s3://``, ``https://``, etc.) are left
    unchanged.
    """
    for i, arg in enumerate(sys.argv[:-1]):
        if arg == '--task-file':
            value = sys.argv[i + 1]
            p = Path(value)
            # Only rewrite bare filenames (no directory components, no URL, not absolute).
            # Paths with directory separators are left to resolve from CWD as the caller
            # intended (e.g. src/metadata_tools/hosts/GO_0xxx/cumulative_tasks.json on GCP).
            if not p.is_absolute() and '://' not in value and p.parent == Path('.'):
                sys.argv[i + 1] = str(host_dir / value)
            break
