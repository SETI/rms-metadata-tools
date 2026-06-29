"""Single cloud entry point for geometry table generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-geometry``: the same work,
distributed across workers. For local runs the basic usage matches ``metadata-geometry``,
and all cloud_tasks arguments are also accepted.

Examples:
 For local runs, the basic usage is identical to metadata-geometry. In addition, all
 cloud_tasks arguments are accepted. For example:

   metadata-geometry-cloud GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \
       --num-simultaneous-tasks 12
   metadata-geometry-cloud GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \
       -vv GO_0017 --num-simultaneous-tasks 12

 For GCP runs:
   - to use the task file used for the index files:
     cloud_tasks run --config gcp_geometry_config.yml --task-file index_tasks.json

   - to use a new task file:
     metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \
         $RMS_METADATA_TEST/GO_0xxx/ -to geometry_tasks.json
     cloud_tasks run --config gcp_geometry_config.yml --task-file geometry_tasks.json --use-spot

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
from typing import Any

from metadata_tools.cli._host import load_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry-cloud HOST_ID [args...]')
    load_host(sys.argv[1])
    sys.path.append('')  # needed for GCP worker instances

    import geometry_config as config
    import host_config as hconf
    from cloud_tasks.worker import Worker, WorkerData

    import metadata_tools.common as com
    import metadata_tools.util as util
    from metadata_tools.geometry_support import get_args, process_tables

    def process_task(_task_id: str,
                     task_data: dict[str, Any],
                     worker_data: WorkerData) -> tuple[bool, Any]:
        process_tables(hconf.template_name,
                       glob=config.glob,
                       index_glob=config.index_glob,
                       selection=config.selection,
                       exclude=config.exclude,
                       args=worker_data.args,
                       volumes=[task_data['volume_id']])
        return False, None

    async def _run() -> None:
        host, _, _ = util.parse_template_name(hconf.template_name)
        parser = get_args(host=host,
                          selection=config.selection,
                          exclude=config.exclude)
        worker = Worker(process_task,
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
