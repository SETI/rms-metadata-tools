# gcloud auth application-default login       # if necessary

# cloud_tasks run --config config1.yaml --task-file test1_tasks.json -vv





# cloud_tasks load_queue --config config.yaml --task-file test_tasks.json -vv
# cloud_tasks manage_pool --config config.yaml -vv

# cloud_tasks monitor_event_queue --config config.yaml --output-file config.log

# cloud_tasks purge_queue --config config.yaml
# cloud_tasks delete_queue --config config.yaml

# gsutil ls gs://rms-metadata-jspitale/test.txt
# gsutil cat gs://rms-metadata-jspitale/test.txt

import sys
from filecache import FCPath

import metadata_tools.util as util

filespec = FCPath('gs://rms-metadata-jspitale/test.txt')
if filespec.exists():
    content = filespec.read_text(encoding='utf-8')
    filespec.write_text(content + '\nGoodbye\nWorld\n', encoding='utf-8')
    exit()

filespec.write_text('Hello\nWorld\n', encoding='utf-8')


from cloud_tasks.worker import Worker, WorkerData

exit()

