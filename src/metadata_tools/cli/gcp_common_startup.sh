set -e

# Mount OOPS-Resources
export INSTANCE_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/name)
gcloud compute instances attach-disk $INSTANCE_NAME --disk=${OOPS_RESOURCES_DISK} --zone=us-central1-a --device-name=nav-resources --mode ro || true

sudo mkdir -p /mnt/nav-resources
sudo mount -o ro /dev/disk/by-id/google-nav-resources-part1 /mnt/nav-resources || true
export OOPS_RESOURCES=/mnt/nav-resources/OOPS-Resources/

# sudo needed for manual paste into instance terminal.
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git
cd /root

if [ -n "${BRANCH:-}" ]; then
    git clone -b "${BRANCH}" --single-branch https://github.com/SETI/rms-metadata-tools.git
    cd rms-metadata-tools
    REPO_DIR="$(pwd)"
    python3 -m venv venv
    # The oops.Host API and the host packages are not released. Remove this command once
    # they are on PyPI.
    "$REPO_DIR/venv/bin/pip" install "rms-oops @ git+https://github.com/SETI/rms-oops@mrs_260925_host_reorg" "rms-host-galileo @ git+https://github.com/SETI/rms-host-galileo@ms_261013_initial_port" "rms-host-cassini @ git+https://github.com/SETI/rms-host-cassini@ms_261004_initial_port"
    "$REPO_DIR/venv/bin/pip" install ".[cloud]"
else
    REPO_DIR="$(pwd)"
    python3 -m venv venv
    "$REPO_DIR/venv/bin/pip" install "rms-metadata-tools[cloud]"
fi
export PATH="$REPO_DIR/venv/bin:$PATH"
