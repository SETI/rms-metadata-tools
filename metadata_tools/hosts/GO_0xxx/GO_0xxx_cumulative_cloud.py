#!/usr/bin/env python
#########################################################################################
# GO_0xxx_cumulative_cloud.py:
#   Generate cumulative tables and labels for Galileo SSI using the cloud_tasks module.
#
# For local runs, the basic usage is identical to GO_0xxx_cumulative.py. In addition, all
# cloud_tasks arguments are accepted. For example:
#
#   python GO_0xxx_cumulative_cloud.py $RMS_METADATA_TEST/GO_0xxx/GO_0999/ --task-file cumulative_tasks.json
#   python GO_0xxx_cumulative_cloud.py $RMS_METADATA_TEST/GO_0xxx/GO_0999/ --task-file cumulative_tasks.json -vv GO_0017
#
# For GCP runs (not yet working), use:
#   gcloud auth application-default login       # if necessary
#
#   - to use the task file used for the index files:
#     cloud_tasks run --config gcp_cumulative_config.yml --task-file cumulative_tasks.json --use-spot
#
#########################################################################################
import asyncio
import sys
from typing import Any
from cloud_tasks.worker import Worker, WorkerData

sys.path.append('')             ### This is needed to get the GCP instance to recognize
                                ### the metadata_tools module
import metadata_tools.util as util

import metadata_tools.common as com
import host_config as hconf
import geometry_config
from metadata_tools.cumulative_support import create_cumulative_indexes, get_args

#========================================================================================
def process_task(_task_id: str,
                 task_data: dict[str, Any],
                 worker_data: WorkerData) -> tuple[bool, Any]:

    # process the volume
    create_cumulative_indexes(hconf.template_name, args=worker_data.args)

    return False, None

#========================================================================================
async def main():
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
