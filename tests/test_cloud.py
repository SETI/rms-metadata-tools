import metadata_tools.util as util
from filecache import FCPath
util.write_txt_file(FCPath('gs://rms-jspitale/test.txt'), ['Hello', 'World'])

# gsutil cat gs://rms-jspitale/test.txt
