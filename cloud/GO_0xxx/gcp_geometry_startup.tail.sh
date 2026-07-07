# Run the geometry code
metadata-geometry-cloud GO_0xxx \
                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/

##  Manual paste into instance..
: <<'COMMENT_BLOCK'
gcloud auth application-default login
metadata-geometry GO_0xxx \
                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/ -vv GO_0022
COMMENT_BLOCK
