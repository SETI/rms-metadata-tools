# gcloud auth application-default login       # if necessary
# python3 test_cloud.py

# gsutil cat gs://rms-jspitale/test.txt

from filecache import FCPath
FCPath('gs://rms-jspitale/test.txt').write_text('Hello\nWorld\n', encoding='utf-8')


# requirements-cloud.txt
# push to githib

# permission
#  Bucket Details --> Grant access -->
#     new principals: jspitale@rms-node-419806.iam.gserviceaccount.com
#     assign role : Cloud Storage --> Storage Admin


