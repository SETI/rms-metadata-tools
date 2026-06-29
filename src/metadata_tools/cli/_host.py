"""Shared host-directory injection for CLI entry points."""
import sys
from pathlib import Path


def load_host(host_id: str) -> None:
    """Inject the host directory into sys.path and remove HOST_ID from sys.argv.

    Resolves hosts/<host_id>/ relative to the installed package, validates it
    exists, prepends it to sys.path (so bare ``import host_config`` etc. resolve),
    and drops HOST_ID from sys.argv so the support module's argparser sees the
    normal positional arguments it expects.
    """
    host_dir = Path(__file__).parent.parent / 'hosts' / host_id
    if not host_dir.is_dir():
        sys.exit(f'Unknown host: {host_id!r} — no directory at {host_dir}')
    sys.path.insert(0, str(host_dir))
    sys.argv = [sys.argv[0]] + sys.argv[2:]
