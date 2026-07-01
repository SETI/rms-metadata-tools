"""Single cloud entry point for geometry table generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-geometry``: the same work,
distributed across workers. For local runs the basic usage matches ``metadata-geometry``,
and all cloud_tasks arguments are also accepted.

Examples:
 For local runs, the basic usage is identical to metadata-geometry. In addition, all
 cloud_tasks arguments are accepted. For example:

   metadata-geometry-cloud GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ --num-simultaneous-tasks 12
   metadata-geometry-cloud GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -vv GO_0017 --num-simultaneous-tasks 12

 For GCP runs:
   - to use the task file used for the index files:
     metadata-geometry-cloud GO_0xxx --config gcp_geometry_config.yml --task-file index_tasks.json

   - to use a new task file:
     metadata-index-cloud GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -to geometry_tasks.json
     metadata-geometry-cloud GO_0xxx --config gcp_geometry_config.yml --task-file geometry_tasks.json --use-spot

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
from typing import Any

from metadata_tools.cli._host import dispatch_cloud_run_if_config, load_host, resolve_host_paths


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
    dispatch_cloud_run_if_config()

    import geometry_config as config
    import host_config as hconf
    from cloud_tasks.worker import Worker

    import metadata_tools.common as com
    import metadata_tools.util as util
    from metadata_tools.geometry_support import get_args, process_tables

    async def _run() -> None:
        host, _, _ = util.parse_template_name(hconf.template_name)
        parser = get_args(host=host,
                          selection=config.selection,
                          exclude=config.exclude)
        worker = Worker(_GeometryTask(host_id, hconf.template_name, config.glob,
                                      config.index_glob, config.selection, config.exclude),
                        task_source=com.task_source,
                        args=sys.argv[1:],
                        argparser=parser)
        args = worker._data.args
        assert args is not None  # nosec B101
        process_tables(hconf.template_name,
                       glob=config.glob,
                       index_glob=config.index_glob,
                       selection=config.selection,
                       exclude=config.exclude,
                       args=args,
                       task_list_only=True,
                       task_file=args.task_file)
        await worker.start()

    asyncio.run(_run())
