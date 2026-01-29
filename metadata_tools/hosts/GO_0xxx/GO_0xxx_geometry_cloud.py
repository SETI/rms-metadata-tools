#!/usr/bin/env python
#########################################################################################
# GO_0xxx_geometry_cloud.py:
#   Generate supplemental geometry tables and labels for Galileo SSI using the cloud_tasks
#   module.
#
# For local runs, the basic usage is identical to GO_0xxx_geometry.py. In addition, all
# cloud_tasks arguments are accepted. For example:
#
#   python GO_0xxx_geometry_cloud.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ --num-simultaneous-tasks 12
#   python GO_0xxx_geometry_cloud.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ $RMS_VOLUMES/GO_0xxx/ -vv GO_0017 --num-simultaneous-tasks 12
#
# For GCP runs (not yet working), use:
#   gcloud auth application-default login       # if necessary
#
#   cloud_tasks load_queue --config gcp_geometry_config.yml --task-file geometry_tasks.json -vv
#   cloud_tasks manage_pool --config gcp_geometry_config.yml -vv
#
#   Other useful commands
#     cloud_tasks monitor_event_queue --config gcp_geometry_config.yml --output-file gcp_geometry_config.log
#
#     cloud_tasks stop --config gcp_geometry_config.yml
#     cloud_tasks purge_queue --config gcp_geometry_config.yml
#     cloud_tasks delete_queue --config gcp_geometry_config.yml
#
#     cloud_tasks show_queue --project-id rms-metadata --job-id metadata-geometry-job --provider gcp --detail
#     cloud_tasks status --project-id rms-metadata --job-id metadata-geometry-job --provider gcp
#     cloud_tasks list_running_instances --project-id rms-metadata --job-id metadata-geometry-job --provider gcp
#
#########################################################################################
import asyncio
import sys
from typing import Any
from cloud_tasks.worker import Worker, WorkerData

import metadata_tools.util as util
import metadata_tools.common as com
import host_config as hconf
import geometry_config as config
from metadata_tools.geometry_support import process_tables, get_args

#========================================================================================
def process_task(_task_id: str,
                 task_data: dict[str, Any],
                 worker_data: WorkerData) -> tuple[bool, Any]:

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
