#!/usr/bin/env python
#########################################################################################
# GO_0xxx_geometry_cloud.py:
#   Generates all geometry tables and labels for Galileo SSI using the cloud_tasks module.
#
# For local runs, the basic usage is identical to GO_0xxx_geometry.py. In addition, all
# cloud_tasks arguments are accepted. For example:
#
#   python GO_0xxx_geometry_cloud.py $RMS_METADATA_TEST/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \
#                                       --num-simultaneous-tasks 12 --max-runtime 10000
#
#
#
#########################################################################################
import asyncio
import sys
from cloud_tasks.worker import Worker, WorkerData

import metadata_tools.util as util
import metadata_tools.common as com
import host_config as hconf
import geometry_config as config
from metadata_tools.geometry_support import process_tables, get_args

#========================================================================================
def process_task(_task_id: str,
                 task_data: dict[str, any],
                 worker_data: WorkerData) -> tuple[bool, any]:

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
async def main():
    # These command line arguments are used to override environment variables when
    # specifying the behavior of the worker process manager. They are optional
    # and most useful when running the worker locally.

    # parse metadata arguments
    host, index_type, template_dir = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host,
                      selection=config.selection,
                      exclude=config.exclude)

    # initialize the worker
    worker = Worker(process_task,
                    task_source=com.task_source,
                    args=sys.argv[1:],
                    argparser=parser)

    # set up the task file containing one entry per volume
    process_tables(hconf.template_name,
                   glob=config.glob,
                   index_glob=config.index_glob,
                   selection=config.selection,
                   exclude=config.exclude,
                   args=worker._data.args,
                   task_list_only=True,
                   task_file=worker._data.args.task_file)

    # queue the processing
    await worker.start()

#########################################################################################
if __name__ == "__main__":
    asyncio.run(main())
