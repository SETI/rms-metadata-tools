# Run the cumulative code
metadata-cumulative-cloud GO_0xxx \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/GO_0999/

##  Manual paste into instance..
: <<'COMMENT_BLOCK'
gcloud auth application-default login
metadata-cumulative-cloud GO_0xxx \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/GO_0999/
COMMENT_BLOCK
