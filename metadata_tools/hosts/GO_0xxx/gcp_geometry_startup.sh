apt-get update -y
apt-get install -y python3 python3-pip python3-venv git
cd
git clone https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export MY_WORKER_DEST_BUCKET=gs://my-bucket/results
python3 GO_0xxx_geometry_cloud.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA/GO_0xxx/
