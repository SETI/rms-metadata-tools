import asyncio
import os, sys
import tempfile
from cloud_tasks.worker import Worker, WorkerData

import metadata_tools.util as util
import host_config as hconf
import index_config as config
from metadata_tools.index_support import process_index, get_args

#===============================================================================
def process_task(task_id: str,
                 task_data: dict[str, any],
                 worker_data: WorkerData) -> tuple[bool, any]:


    # process the volume
    process_index(hconf.template_name,
                  glob=config.glob,
                  args=worker_data.args,
                  volumes=[task_data['volume_id']], task_file=worker_data.task_file)

#    return (status tuple)
    return False, 'test'

#===============================================================================
async def main():
    # These command line arguments are used to override environment variables when
    # specifying the behavior of the worker process manager. They are optional
    # and most useful when running the worker locally.

    # parse metadata arguments
    host, index_type = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, index_type=index_type)

    tempdir = tempfile.mkdtemp()
    task_file = os.path.join(tempdir, 'tasks.json')
    print(task_file) #######################

    # initialize the worker
    worker = Worker(process_task,
                    args=sys.argv[1:], argparser=parser, task_file=task_file)

    # set up the task file containing one entry per volume

    process_index(hconf.template_name,
                  glob=config.glob,
                  args=worker._data.args,
                  task_file_only=True, task_file=task_file)

    # queue the processing
    await worker.start()

    # cleanup
    ############ need a cleanup function that's called at end or when interrupted'
    os.remove(task_file)
    os.path.rmdir(tempdir)

################################################################################
if __name__ == "__main__":
    asyncio.run(main())