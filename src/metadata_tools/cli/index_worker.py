"""Local worker entry point for supplemental index generation across all hosts.

This is the rms-cloud-tasks worker counterpart of ``metadata-index``: the same work,
distributed across local Worker processes.  Basic usage matches ``metadata-index``;
all cloud_tasks Worker arguments are also accepted.

GCP VMs launched by ``metadata-index-cloud`` invoke this entry point via the startup
script.  For local parallelism without GCP, use this command directly:

  metadata-index-worker GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \\
      $RMS_METADATA_TEST/GO_0xxx/ --volumes GO_0022 GO_0016 --num-simultaneous-tasks 12

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
from metadata_tools.config import get_host_config, get_index_config, set_host


class _IndexTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str, glob: str | None) -> None:
        self._host_id = host_id
        self._template_name = template_name
        self._glob = glob

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        set_host(self._host_id)
        from metadata_tools.index_support import process_index
        process_index(self._template_name, glob=self._glob,
                      args=worker_data.args, volumes=[task_data['volume_id']])
        return False, None


def main() -> None:
    """Entry point for the ``metadata-index-worker`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index-worker HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))

    set_host(host_id)
    hconf = get_host_config()
    config = get_index_config()

    import metadata_tools.util as util
    from metadata_tools.index_support import get_args

    host, index_type, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, index_type=index_type)

    run_cloud_worker(parser, _IndexTask(host_id, hconf.template_name, config.glob))
