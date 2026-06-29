"""Single cloud entry point for supplemental index generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-index``: the same work,
distributed across workers. For local runs the basic usage matches ``metadata-index``,
and all cloud_tasks arguments are also accepted.

Examples:
 For local runs, the basic usage is identical to metadata-index. In addition, all
 cloud_tasks arguments are accepted. For example:

   metadata-index-cloud GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \
       $RMS_METADATA_TEST/GO_0xxx/ --num-simultaneous-tasks 12
   metadata-index-cloud GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \
       $RMS_METADATA_TEST/GO_0xxx/ -vv GO_0017 --num-simultaneous-tasks 12

 For GCP runs (not yet working), use:
   gcloud auth application-default login       # if necessary

   metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \
       $RMS_METADATA_TEST/GO_0xxx/ -to index_tasks.json
   cloud_tasks run --config gcp_index_config.yml --task-file index_tasks.json --use-spot

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
from typing import Any

from metadata_tools.cli._host import load_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index-cloud HOST_ID [args...]')
    load_host(sys.argv[1])
    sys.path.append('')  # needed for GCP worker instances

    import host_config as hconf
    import index_config as config
    from cloud_tasks.worker import Worker, WorkerData

    import metadata_tools.common as com
    import metadata_tools.util as util
    from metadata_tools.index_support import get_args, process_index

    def process_task(_task_id: str,
                     task_data: dict[str, Any],
                     worker_data: WorkerData) -> tuple[bool, Any]:
        process_index(hconf.template_name,
                      glob=config.glob,
                      args=worker_data.args,
                      volumes=[task_data['volume_id']])
        return False, None

    async def _run() -> None:
        host, index_type, _ = util.parse_template_name(hconf.template_name)
        parser = get_args(host=host, index_type=index_type)
        worker = Worker(process_task,
                        task_source=com.task_source,
                        args=sys.argv[1:],
                        argparser=parser)
        args = worker._data.args
        assert args is not None  # nosec B101
        process_index(hconf.template_name,
                      glob=config.glob,
                      args=args,
                      task_list_only=True,
                      task_file=args.task_file)
        await worker.start()

    asyncio.run(_run())
