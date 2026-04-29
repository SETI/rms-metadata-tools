#!/bin/bash

######## index / geometry common code ####################################################
# sudo needed for manual paste into instance terminal..
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git
cd

#git clone https://github.com/SETI/rms-metadata-tools.git
git clone -b jns--updates-continued --single-branch https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
##########################################################################################

# Run the index code
python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_index_cloud.py \
                gs://rms-node-holdings/pds3-holdings/volumes/GO_0xxx/ \
                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/




##  Manual paste into instance..
#export GCLOUD_PROJECT="rms-metadata"
#gcloud auth application-default login
#python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_index.py \
#                gs://rms-node-holdings/pds3-holdings/volumes/GO_0xxx/ \
#                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
#                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/ -vv GO_0002
