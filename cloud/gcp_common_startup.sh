# Mount OOPS-Resources
export INSTANCE_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/name)
gcloud compute instances attach-disk $INSTANCE_NAME --disk=standard-oops-resources-central1-a-1 --zone=us-central1-a --device-name=nav-resources --mode ro

sudo mkdir -p /mnt/nav-resources
sudo mount -o ro /dev/disk/by-id/google-nav-resources-part1 /mnt/nav-resources
export OOPS_RESOURCES=/mnt/nav-resources/OOPS-Resources/

# sudo needed for manual paste into instance terminal.
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git
cd

#git clone https://github.com/SETI/rms-metadata-tools.git
git clone -b jns-updates-claude --single-branch https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python3 -m venv venv
source venv/bin/activate
pip install ".[cloud]"
