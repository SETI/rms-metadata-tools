#!/bin/bash
# source "${BASH_SOURCE%/*}gcp_startup_common.sh
python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_geometry_cloud.py \
                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/


