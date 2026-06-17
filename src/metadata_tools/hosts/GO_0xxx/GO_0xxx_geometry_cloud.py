#!/usr/bin/env python
"""Generate geometry tables and labels for Galileo SSI via cloud_tasks.

This is the rms-cloud-tasks (GCP) counterpart of GO_0xxx_geometry.py: the same work,
distributed across workers. For local runs the basic usage matches GO_0xxx_geometry.py,
and all cloud_tasks arguments are also accepted. Run this script from inside its host
directory (hosts/GO_0xxx), because it does top-level ``import host_config`` /
``import geometry_config`` which only resolve when the host directory is on sys.path.

Example (local):
    python GO_0xxx_geometry_cloud.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \\
        --num-simultaneous-tasks 12

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
from typing import Any

from cloud_tasks.worker import Worker, WorkerData

sys.path.append('')             ### This is needed to get the GCP instance to recognize
                                ### the metadata_tools module
import geometry_config as config
import host_config as hconf

import metadata_tools.common as com
import metadata_tools.util as util
from metadata_tools.geometry_support import get_args, process_tables


#========================================================================================
def process_task(_task_id: str,
                 task_data: dict[str, Any],
                 worker_data: WorkerData) -> tuple[bool, Any]:
    """Process one volume's geometry tables as a single cloud task.

    Parameters:
        _task_id: Identifier of the cloud task (unused).
        task_data: Task payload; must contain the 'volume_id' to process.
        worker_data: Shared worker data carrying the parsed CLI arguments.

    Returns:
        A (retry, result) tuple as expected by the cloud_tasks worker.
    """
    # process the volume
    process_tables(hconf.template_name,
                   glob=config.glob,
                   index_glob=config.index_glob,
                   selection=config.selection,
                   exclude=config.exclude,
                   args=worker_data.args,
                   volumes=[task_data['volume_id']])

    return False, None

#========================================================================================
async def main() -> None:
    """Build the per-volume task file and run the cloud_tasks worker."""
    # These command line arguments are used to override environment variables when
    # specifying the behavior of the worker process manager. They are optional
    # and most useful when running the worker locally.

    # parse metadata arguments
    host, _index_type, _template_dir = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host,
                      selection=config.selection,
                      exclude=config.exclude)

    # initialize the worker
    worker = Worker(process_task,
                    task_source=com.task_source,
                    args=sys.argv[1:],
                    argparser=parser)

    # set up the task file containing one entry per volume
    args = worker._data.args
    assert args is not None  # nosec B101 - type-narrowing invariant, not validation
    process_tables(hconf.template_name,
                   glob=config.glob,
                   index_glob=config.index_glob,
                   selection=config.selection,
                   exclude=config.exclude,
                   args=args,
                   task_list_only=True,
                   task_file=args.task_file)

    # queue the processing
    await worker.start()

#########################################################################################
if __name__ == "__main__":
    asyncio.run(main())
