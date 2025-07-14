#!/usr/bin/env python
#########################################################################################
# GO_0xxx_index.py:
#   Generate supplemental index tables and labels for Galileo SSI using the cloud_tasks
#   module.
#
# For local runs, the basic usage is identical to GO_0xxx_index.py. In addition, all
# cloud_tasks arguments are accepted. For example:
#
#   python GO_0xxx_index_cloud.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ --num-simultaneous-tasks 12
#
#
# cloud_tasks run --config gcp_index_config.yml --project-id rms-node-419806 --task-file index_tasks.json
#
#
#########################################################################################
import asyncio
import os, sys
from cloud_tasks.worker import Worker, WorkerData

import metadata_tools.util as util
import metadata_tools.common as com
import host_config as hconf
import index_config as config
from metadata_tools.index_support import process_index, get_args

#========================================================================================
def process_task(task_id: str,
                 task_data: dict[str, any],
                 worker_data: WorkerData) -> tuple[bool, any]:

    # process the volume
    process_index(hconf.template_name,
                  glob=config.glob,
                  args=worker_data.args,
                  volumes=[task_data['volume_id']])

    return False, None

#========================================================================================
async def main():
    # These command line arguments are used to override environment variables when
    # specifying the behavior of the worker process manager. They are optional
    # and most useful when running the worker locally.

    # parse metadata arguments
    host, index_type = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, index_type=index_type)

    # initialize the worker
    worker = Worker(process_task,
                    task_source=com.task_source,
                    args=sys.argv[1:],
                    argparser=parser)

    # set up the task file containing one entry per volume
    process_index(hconf.template_name,
                  glob=config.glob,
                  args=worker._data.args,
                  task_list_only=True,
                  task_file=worker._data.args.task_file)

    # queue the processing
    await worker.start()

#########################################################################################
if __name__ == "__main__":
    asyncio.run(main())
