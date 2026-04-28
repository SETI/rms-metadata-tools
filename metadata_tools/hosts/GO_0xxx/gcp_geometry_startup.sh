#!/bin/bash
##  gcloud auth application-default login        # needed for manual paste into instance
export GCLOUD_PROJECT="rms-metadata"             # terminal

# sudo needed for manual paste into instance terminal..
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git
cd





###  modified unmerged oops branch...
git clone -b jns-host-updates --single-branch https://github.com/SETI/rms-oops.git
pip install -e ~/rms-oops/
###




#git clone https://github.com/SETI/rms-metadata-tools.git
git clone -b jns--updates-continued --single-branch https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Mount OOPS-Resources
export INSTANCE_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/name)
gcloud compute instances attach-disk $INSTANCE_NAME --disk=ssd-oops-resources-central1-a-1 --zone=us-central1-a --device-name=nav-resources
sudo mkdir -p /mnt/nav-resources
sudo mount -o ro /dev/disk/by-id/google-nav-resources-part1 /mnt/nav-resources
export OOPS_RESOURCES=/mnt/nav-resources/OOPS-Resources/



# Run the geometry code
python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_geometry_cloud.py \
                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/








#python3 metadata_tools/hosts/GO_0xxx/GO_0xxx_geometry.py \
#                gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ \
#                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/ -vv GO_0002
