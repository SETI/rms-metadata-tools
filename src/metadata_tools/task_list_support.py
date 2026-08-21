##########################################################################################
# task_list_support.py: Standalone task list support for cloud/Worker runs
##########################################################################################
"""Task list creation and volume scanning for cloud/Worker metadata runs.

Provides :func:`task_generator` for building tasks from an explicit volume list and
:func:`scan_volumes` for discovering volumes by walking a directory tree (the logic
formerly embedded in ``_create_index`` and ``process_tables``).
"""
import fnmatch
import json
from collections.abc import Iterator
from typing import Any

from filecache import FCPath

import metadata_tools.util as util


#=========================================================================================
def make_task(volume_id: str) -> dict[str, Any]:
    """Build a single task dict for *volume_id*.

    Parameters:
        volume_id: Volume ID (e.g. ``'GO_0017'``).

    Returns:
        Task dict with keys ``task_id`` and ``data``.
    """
    return {'task_id': f'task-{volume_id}', 'data': {'volume_id': volume_id}}


#=========================================================================================
def task_generator(volumes: list[str]) -> Iterator[dict[str, Any]]:
    """Yield one task dict per volume without requiring a filesystem scan.

    Parameters:
        volumes: Ordered list of volume IDs to generate tasks for.

    Yields:
        Task dicts compatible with ``cloud_tasks.worker.Worker``.
    """
    for vol in volumes:
        yield make_task(vol)


#=========================================================================================
def scan_volumes(tree: FCPath) -> list[str]:
    """Walk *tree* and return the sorted list of volume IDs it contains.

    Volumes are identified by matching the last path component against the glob
    derived from the tree's own name via :func:`~metadata_tools.util.get_volume_glob`.
    Directories named ``__skip`` are ignored.

    Parameters:
        tree: Top of the directory tree to scan.  Pass ``volume_tree`` for index
              runs or ``output_tree`` / ``metadata_tree`` for geometry runs.

    Returns:
        Sorted list of volume IDs found in *tree*.
    """
    vol_glob = util.get_volume_glob(tree.name)
    volumes: list[str] = []
    for root, dirs, _files in tree.walk():
        if '__skip' in root.as_posix():
            continue
        dirs.sort()
        vol = FCPath(root).parts[-1]
        if fnmatch.filter([vol], vol_glob):
            volumes.append(vol)
    return sorted(volumes)


#=========================================================================================
def write_task_file(volumes: list[str], output: str | FCPath) -> None:
    """Write a JSON task list file for *volumes*.

    Parameters:
        volumes: Volume IDs to include.
        output: Destination file path (local or remote).
    """
    tasks = list(task_generator(volumes))
    FCPath(output).write_text(json.dumps(tasks, indent=2), encoding='utf-8')
