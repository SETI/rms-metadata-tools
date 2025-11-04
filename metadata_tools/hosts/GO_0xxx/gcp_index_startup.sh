apt-get update -y
# Reading package lists... Done
# E: Could not open lock file /var/lib/apt/lists/lock - open (13: Permission denied)
# E: Unable to lock directory /var/lib/apt/lists/


apt-get install -y python3 python3-pip python3-venv git
cd
git clone https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export MY_WORKER_DEST_BUCKET=gs://my-bucket/results
#python3 GO_0xxx_index_cloud.py gs://rms-node-holdings/pds3-holdings/volumes/GO_0xxx/ gs://rms-node-metadata/GO_0xxx/ --index_tree gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/
python3 GO_0xxx_geometry.py gs://rms-node-holdings/pds3-holdings/volumes/GO_0xxx/ gs://rms-node-metadata/GO_0xxx/ --index_tree gs://rms-node-holdings/pds3-holdings/metadata/GO_0xxx/ GO_0017


### could this be done with a snapshot?

### BadRequestException: 400 Bucket is a requester pays bucket but no user project provided.