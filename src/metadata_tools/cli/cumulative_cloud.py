"""Single cloud entry point for cumulative table generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-cumulative``: the same work,
distributed across workers. GCP runs are not yet working. For local runs the basic usage
matches ``metadata-cumulative``, and all cloud_tasks arguments are also accepted.

Examples:
 For local runs, the basic usage is identical to metadata-cumulative. In addition, all
 cloud_tasks arguments are accepted. For example:

   metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/ \
       --task-file cumulative_tasks.json
   metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/ \
       --task-file cumulative_tasks.json -vv GO_0017

 For GCP runs, use:
   gcloud auth application-default login       # if necessary

   - to use the task file used for the index files:
     cloud_tasks run --config gcp_cumulative_config.yml --task-file cumulative_tasks.json --use-spot

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
from typing import Any

from metadata_tools.cli._host import load_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative-cloud HOST_ID [args...]')
    load_host(sys.argv[1])
    sys.path.append('')  # needed for GCP worker instances

    import geometry_config  # noqa: F401  (side effects: column registration)
    import host_config as hconf
    from cloud_tasks.worker import Worker, WorkerData

    import metadata_tools.util as util
    from metadata_tools.cumulative_support import create_cumulative_indexes, get_args

    def process_task(_task_id: str,
                     task_data: dict[str, Any],
                     worker_data: WorkerData) -> tuple[bool, Any]:
        create_cumulative_indexes(hconf.template_name, args=worker_data.args)
        return False, None

    async def _run() -> None:
        host, _, _ = util.parse_template_name(hconf.template_name)
        parser = get_args(host=host)
        worker = Worker(process_task,
                        args=sys.argv[1:],
                        argparser=parser)
        await worker.start()

    asyncio.run(_run())
