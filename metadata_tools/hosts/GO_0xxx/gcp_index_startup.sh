#!/bin/bash

apt-get update -y
apt-get install -y python3 python3-pip python3-venv git


source "${BASH_SOURCE%/*}gcp_startup_common.sh


python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_index_cloud.py \
                gs://rms-node-holdings/pds3-holdings/volumes/GO_0xxx/ \
                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/




