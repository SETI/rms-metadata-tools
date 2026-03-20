#!/bin/bash
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git
cd
#git clone https://github.com/SETI/rms-metadata-tools.git
git clone -b jns--updates-continued --single-branch https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
##cd hosts/GO_0xxx
python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_index_cloud.py gs://rms-node-holdings/pds3-holdings/volumes/GO_0xxx/ gs://rms-node-metadata/GO_0xxx/ gs://rms-metadata-jspitale/metadata_test/GO_000x



