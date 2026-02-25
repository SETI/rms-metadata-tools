apt-get update -y
apt-get install -y python3 python3-pip python3-venv git
cd
if [ ! -d rms-metadata-tools ]; then
#  git clone https://github.com/SETI/rms-metadata-tools.git
  git clone -b jns--updates-continued --single-branch https://github.com/SETI/rms-metadata-tools.git
  cd rms-metadata-tools
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements-cloud.txt
else
  cd rms-metadata-tools
fi

cd cloud_tests/test2
python3 cloud_test2.py

