# Run the cumulative code
metadata-cumulative-cloud GO_0xxx \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/GO_0999/ \
                --task-file src/metadata_tools/hosts/GO_0xxx/cumulative_tasks.json

##  Manual paste into instance..
: <<'COMMENT_BLOCK'
gcloud auth application-default login
metadata-cumulative-cloud GO_0xxx \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/GO_0999/ \
                --task-file src/metadata_tools/hosts/GO_0xxx/cumulative_tasks.json
COMMENT_BLOCK
