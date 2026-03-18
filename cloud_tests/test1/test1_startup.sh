apt-get update -y
apt-get install -y python3 python3-pip python3-venv git
cd || exit 1
#git clone https://github.com/SETI/rms-metadata-tools.git || exit 1
git clone -b jns--updates-continued --single-branch https://github.com/SETI/rms-metadata-tools.git || exit 1
cd rms-metadata-tools || exit 1
python3 -m venv venv || exit 1
source venv/bin/activate || { echo 'No virtual environment' ; exit 1; }
pip install -r requirements-cloud.txt

###cd cloud_tests/test1
python3 cloud_tests/test1/cloud_test1.py

