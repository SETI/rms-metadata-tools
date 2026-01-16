#!/bin/bash
apt-get update -y

apt-get install -y python3 python3-pip python3-venv git
cd || exit 1
git clone https://github.com/SETI/rms-metadata-tools.gitnew_overrides
cd rms-metadata-tools || exit 1
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd hosts/GO_0xxx || exit 1
python3 GO_0xxx_index_cloud.py gs://rms-node-holdings/pds3-holdings/volumes/GO_0xxx/ gs://rms-node-metadata/GO_0xxx/ --index_tree gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/



