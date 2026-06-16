#!/usr/bin/env python
"""Generate cumulative tables and labels for Galileo SSI via cloud_tasks.

This is the rms-cloud-tasks (GCP) counterpart of GO_0xxx_cumulative.py: the same work,
distributed across workers. GCP runs are not yet working. For local runs the basic usage
matches GO_0xxx_cumulative.py, and all cloud_tasks arguments are also accepted. Run this
script from inside its host directory (hosts/GO_0xxx), because it does top-level
``import host_config`` which only resolves when the host directory is on sys.path.

Example (local):
    python GO_0xxx_cumulative_cloud.py $RMS_METADATA_TEST/GO_0xxx/GO_0999/ \\
        --task-file cumulative_tasks.json

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
from typing import Any

from cloud_tasks.worker import Worker, WorkerData

sys.path.append('')             ### This is needed to get the GCP instance to recognize
                                ### the metadata_tools module
import geometry_config  # noqa: F401  (host plugin side-effect import)
import host_config as hconf

import metadata_tools.util as util
from metadata_tools.cumulative_support import create_cumulative_indexes, get_args


#========================================================================================
def process_task(_task_id: str,
                 task_data: dict[str, Any],
                 worker_data: WorkerData) -> tuple[bool, Any]:
    """Build the cumulative tables as a single cloud task.

    Parameters:
        _task_id: Identifier of the cloud task (unused).
        task_data: Task payload (unused).
        worker_data: Shared worker data carrying the parsed CLI arguments.

    Returns:
        A (retry, result) tuple as expected by the cloud_tasks worker.
    """
    # process the volume
    create_cumulative_indexes(hconf.template_name, args=worker_data.args)

    return False, None

#========================================================================================
async def main() -> None:
    """Run the cloud_tasks worker to build the cumulative tables."""
    # These command line arguments are used to override environment variables when
    # specifying the behavior of the worker process manager. They are optional
    # and most useful when running the worker locally.

    # parse metadata arguments
    host, _index_type, _template_dir = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host)

    # initialize the worker
    worker = Worker(process_task,
                    args=sys.argv[1:],
                    argparser=parser)

    # queue the processing
    await worker.start()

#########################################################################################
if __name__ == "__main__":
    asyncio.run(main())
