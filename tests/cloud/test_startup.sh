apt-get update -y
apt-get install -y python3 python3-pip python3-venv git
cd
git clone https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python3 -m venv venv
source venv/bin/activate
#pip install -r requirements-cloud.txt
pip install -r requirements.txt

cd tests/cloud
python3 test_cloud.py

