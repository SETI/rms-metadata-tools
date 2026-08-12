"""Local worker entry point for cumulative table generation across all hosts.

This is the rms-cloud-tasks worker counterpart of ``metadata-cumulative``: the same work,
run via a cloud_tasks Worker.  Basic usage is identical to ``metadata-cumulative``;
all cloud_tasks Worker arguments are also accepted.

GCP VMs launched by ``metadata-cumulative-cloud`` invoke this entry point via the startup
script.  For local runs, use this command directly:

  metadata-cumulative-worker GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/
  metadata-cumulative-worker GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/ --volumes GO_0017

The full list of command-line options is documented in the user guide.
"""
import sys
from typing import Any

from metadata_tools.cli._host import (
    cloud_dir_for,
    load_host,
    resolve_host_paths,
    run_cloud_worker,
    single_task_as_task_file,
)
from metadata_tools.config import get_host_config, set_host


class _CumulativeTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str,
                 exclude: list[str] | None) -> None:
        self._host_id = host_id
        self._template_name = template_name
        self._exclude = exclude

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        set_host(self._host_id)
        from copy import copy

        from filecache import FileCache

        from metadata_tools.cumulative_support import create_cumulative_indexes

        # Private auto-deleting cache reclaims read tables per task (global cache never
        # evicts); write_text uploads on close so remote output survives cache deletion.
        with FileCache(cache_name=None, delete_on_exit=True) as fc:
            args = copy(worker_data.args)
            if getattr(args, 'output_dir', None) is not None:
                args.output_dir = fc.new_path(args.output_dir)
            create_cumulative_indexes(self._template_name, args=args,
                                      exclude=self._exclude)
        return False, None


def main() -> None:
    """Entry point for the ``metadata-cumulative-worker`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative-worker HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))

    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.util as util
    from metadata_tools.cumulative_support import get_args

    host, _, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host)

    with single_task_as_task_file():
        run_cloud_worker(parser,
                         _CumulativeTask(host_id, hconf.template_name, hconf.exclude),
                         supports_volumes=False)
