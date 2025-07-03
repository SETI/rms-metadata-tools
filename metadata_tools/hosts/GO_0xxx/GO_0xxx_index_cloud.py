import asyncio
import sys
from cloud_tasks.worker import Worker, WorkerData

import metadata_tools.common as com
import metadata_tools.util as util

###from main import processing_function  # This will get all of your processing code without running main()
import host_config as hconf
import index_config as config
from metadata_tools.index_support import process_index, _get_args

#===============================================================================
def process_task(task_id: str,
                 task_data: dict[str, any],
                 worker_data: WorkerData) -> tuple[bool, any]:
    # Parse out task_id and task_data here to create whatever info your processing code needs

    process_index(hconf.template_name, glob=config.glob, args=worker_data.args)
#    return (status tuple)
    return False, 'test'

#===============================================================================
async def main():
    # These command line arguments are used to override environment variables when
    # specifying the behavior of the worker process manager. They are optional
    # and most useful when running the worker locally.

    host, index_type = util.parse_template_name(hconf.template_name)
    parser = _get_args(host=host, index_type=index_type)

    worker = Worker(process_task, args=sys.argv[1:], argparser=parser)
    await worker.start()

################################################################################
if __name__ == "__main__":
    asyncio.run(main())