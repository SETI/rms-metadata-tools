# gcloud auth application-default login       # if necessary

# cloud_tasks run --config config1.yaml --task-file test1_tasks.json -vv





# cloud_tasks load_queue --config config.yaml --task-file test_tasks.json -vv
# cloud_tasks manage_pool --config config.yaml -vv

# cloud_tasks monitor_event_queue --config config.yaml --output-file config.log

# cloud_tasks purge_queue --config config.yaml
# cloud_tasks delete_queue --config config.yaml

# gsutil ls gs://rms-metadata-jspitale/test.txt
# gsutil cat gs://rms-metadata-jspitale/test.txt



import asyncio
import multiprocessing
import sys
from cloud_tasks.worker import Worker, WorkerData
from filecache import FCPath

import sys
sys.path.append('')

import metadata_tools.util as util

#========================================================================================
def process_task(task_id: str,
                 task_data: dict[str, any],
                 worker_data: WorkerData) -> tuple[bool, any]:

    filespec = FCPath('gs://rms-metadata-jspitale/test.txt')
    worker_id = multiprocessing.current_process().name

#    filespec.write_text(f"Hello from {worker_id}\n")
#    util.append_txt_file(filespec, f"Hello from {worker_id}!\n")

    content = ''
    if filespec.exists():
        content = util.read_txt_file(filespec)
    util.write_txt_file(filespec, content + [f"Hello from {worker_id}!\n"])

    return False, None

#========================================================================================
async def main():

    worker = Worker(process_task, args=sys.argv[1:])
    await worker.start()

#########################################################################################
if __name__ == "__main__":
    asyncio.run(main())
