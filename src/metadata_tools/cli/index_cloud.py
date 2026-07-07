"""Single cloud entry point for supplemental index generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-index``: the same work,
distributed across workers. For local runs the basic usage matches ``metadata-index``,
and all cloud_tasks arguments are also accepted.

Examples:
 For local runs with explicit volumes via the task source:

   metadata-index-cloud GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \\
       $RMS_METADATA_TEST/GO_0xxx/ --volumes GO_0022 GO_0016 --num-simultaneous-tasks 12

 For GCP runs, first generate a task file:

   metadata-task-list GO_0xxx $RMS_VOLUMES/GO_0xxx/ --output tasks.json

 Then dispatch:

   metadata-index-cloud GO_0xxx --use-spot \
       --config cloud/GO_0xxx/gcp_index_config.yml --task-file cloud/GO_0xxx/tasks.json

 Or dispatch directly from a volume list (task file is generated automatically):

   metadata-index-cloud GO_0xxx --use-spot \
       --config cloud/GO_0xxx/gcp_index_config.yml --volumes GO_0022 GO_0016

The full list of command-line options is documented in the user guide.
"""
import sys
from typing import Any

from metadata_tools.cli._host import (
    cloud_dir_for,
    dispatch_cloud_run_if_config,
    load_host,
    resolve_host_paths,
    run_cloud_worker,
    volumes_as_task_file,
)


class _IndexTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str, glob: str | None) -> None:
        self._host_id = host_id
        self._template_name = template_name
        self._glob = glob

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        load_host(self._host_id)
        from metadata_tools.index_support import process_index
        process_index(self._template_name, glob=self._glob,
                      args=worker_data.args, volumes=[task_data['volume_id']])
        return False, None


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))
    with volumes_as_task_file():
        rc = dispatch_cloud_run_if_config()
    if rc is not None:
        sys.exit(rc)

    import host_config as hconf
    import index_config as config

    import metadata_tools.util as util
    from metadata_tools.index_support import get_args

    host, index_type, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, index_type=index_type)
    run_cloud_worker(parser, _IndexTask(host_id, hconf.template_name, config.glob))
