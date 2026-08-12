"""Local worker entry point for geometry table generation across all hosts.

This is the rms-cloud-tasks worker counterpart of ``metadata-geometry``: the same work,
distributed across local Worker processes.  Basic usage matches ``metadata-geometry``;
all cloud_tasks Worker arguments are also accepted.

GCP VMs launched by ``metadata-geometry-cloud`` invoke this entry point via the startup
script.  For local parallelism without GCP, use this command directly:

  metadata-geometry-worker GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \\
      --volumes GO_0022 GO_0016 --num-simultaneous-tasks 12

The full list of command-line options is documented in the user guide.
"""
import sys
from typing import Any

from metadata_tools.cli._host import (
    cloud_dir_for,
    load_host,
    resolve_host_paths,
    run_cloud_worker,
)
from metadata_tools.config import get_geometry_config, get_host_config, set_host


class _GeometryTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str, glob: str | None,
                 index_glob: str | None, selection: str | None,
                 exclude: list[str] | None) -> None:
        self._host_id = host_id
        self._template_name = template_name
        self._glob = glob
        self._index_glob = index_glob
        self._selection = selection
        self._exclude = exclude

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        set_host(self._host_id)
        from copy import copy

        from filecache import FileCache

        from metadata_tools.geometry_support import process_tables

        # Private auto-deleting cache reclaims downloaded index files per task; the
        # global cache never evicts on single-instance GCP runs, exhausting the boot disk.
        with FileCache(cache_name=None, delete_on_exit=True) as fc:
            args = copy(worker_data.args)
            if getattr(args, 'metadata_tree', None) is not None:
                args.metadata_tree = fc.new_path(args.metadata_tree)
            process_tables(self._template_name,
                           glob=self._glob,
                           index_glob=self._index_glob,
                           selection=self._selection,
                           exclude=self._exclude,
                           args=args,
                           volumes=[task_data['volume_id']])
        return False, None


def main() -> None:
    """Entry point for the ``metadata-geometry-worker`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry-worker HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))

    set_host(host_id)
    hconf = get_host_config()
    config = get_geometry_config()

    import metadata_tools.util as util
    from metadata_tools.geometry_support import get_args

    host, _, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, selection=config.selection, exclude=config.exclude)

    run_cloud_worker(parser, _GeometryTask(host_id, hconf.template_name,
                                           config.glob, config.index_glob,
                                           config.selection, config.exclude))
