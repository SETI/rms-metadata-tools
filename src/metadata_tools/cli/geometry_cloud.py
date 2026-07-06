"""Single cloud entry point for geometry table generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-geometry``: the same work,
distributed across workers. For local runs the basic usage matches ``metadata-geometry``,
and all cloud_tasks arguments are also accepted.

Examples:
 For local runs with explicit volumes via the task source:

   metadata-geometry-cloud GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \\
       --volumes GO_0017 GO_0018 --num-simultaneous-tasks 12

 For GCP runs, first generate a task file:

   metadata-task-list GO_0xxx $RMS_METADATA/GO_0xxx/ --output tasks.json

 Then dispatch:

   metadata-geometry-cloud GO_0xxx --config gcp_geometry_config.yml --task-file tasks.json --use-spot

 Or dispatch directly from a volume list (task file is generated automatically):

   metadata-geometry-cloud GO_0xxx --config gcp_geometry_config.yml --volumes GO_0017 GO_0018 --use-spot

The full list of command-line options is documented in the user guide.
"""
import sys
from typing import Any

from metadata_tools.cli._host import (
    dispatch_cloud_run_if_config,
    load_host,
    resolve_host_paths,
    run_cloud_worker,
    volumes_to_task_file_if_needed,
)


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
        load_host(self._host_id)
        from metadata_tools.geometry_support import process_tables
        process_tables(self._template_name,
                       glob=self._glob,
                       index_glob=self._index_glob,
                       selection=self._selection,
                       exclude=self._exclude,
                       args=worker_data.args,
                       volumes=[task_data['volume_id']])
        return False, None


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir)
    volumes_to_task_file_if_needed()
    dispatch_cloud_run_if_config()

    import geometry_config as config
    import host_config as hconf

    import metadata_tools.util as util
    from metadata_tools.geometry_support import get_args

    host, _, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, selection=config.selection, exclude=config.exclude)
    run_cloud_worker(parser, _GeometryTask(host_id, hconf.template_name,
                                           config.glob, config.index_glob,
                                           config.selection, config.exclude))
