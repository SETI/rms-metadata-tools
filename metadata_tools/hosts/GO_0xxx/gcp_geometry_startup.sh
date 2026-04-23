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

## -------------------------------------------------------
## Additional instance shell commands
##  gcloud auth application-default login
##  export GCLOUD_PROJECT="rms-metadata"
## -------------------------------------------------------

sudo mkdir -p /mnt/pd1
sudo mount -o ro /dev/disk/by-id/google-oops-resources-part1 /mnt/pd1

sudo mkdir /mnt/pd1/OOPS-Resources
sudo chown $USER /mnt/pd1/OOPS-Resources
gsutil -m rsync -r gs://rms-node-oops-resources /mnt/pd1/OOPS-Resources


python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_geometry_cloud.py \
                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/


