set -e

# Mount OOPS-Resources
export INSTANCE_NAME=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/name)
gcloud compute instances attach-disk $INSTANCE_NAME --disk=${OOPS_RESOURCES_DISK} --zone=us-central1-a --device-name=nav-resources --mode ro || true

sudo mkdir -p /mnt/nav-resources
sudo mount -o ro /dev/disk/by-id/google-nav-resources-part1 /mnt/nav-resources || true
export OOPS_RESOURCES=/mnt/nav-resources/OOPS-Resources/

cd /root

# Every path below is derived from VENV_DIR rather than hard-coded, so the
# SSH-pastable variant (which runs as an ordinary user, not root) can
# relocate the environment by exporting VENV_DIR in its header.
VENV_DIR="${VENV_DIR:-/root/venv}"

# A baked image (scripts/build-gcp-image.sh) ships the venv with the
# release that was current at bake time preinstalled; build the
# environment from scratch only when it is absent (stock Ubuntu image).
if [ ! -d "${VENV_DIR}" ]; then
    # sudo needed for manual paste into instance terminal.
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git
    python3 -m venv "${VENV_DIR}"
    if [ -z "${BRANCH:-}" ]; then
        "${VENV_DIR}/bin/pip" install "rms-metadata-tools[cloud]"
    fi
else
    # Staleness guard: the baked venv freezes whatever release existed
    # when the image was built. Upgrade-if-needed brings a stale image up
    # to the current PyPI release in seconds (a no-op resolve when the
    # image is current), so an old image can never silently run old code.
    # rms-cloud-tasks is named explicitly: the [cloud] extra's version
    # floor alone would not pull a newer release.
    if [ -z "${BRANCH:-}" ]; then
        "${VENV_DIR}/bin/pip" install --upgrade "rms-metadata-tools[cloud]" rms-cloud-tasks
    fi
fi

# A BRANCH build installs the branch into the venv; on a baked image the
# heavy dependencies are already present, so this is quick. git is present
# on a stock image (installed above) but a baked image only carries what
# the bake put there, so check rather than assume.
if [ -n "${BRANCH:-}" ]; then
    command -v git >/dev/null 2>&1 || sudo apt-get install -y git
    git clone -b "${BRANCH}" --single-branch https://github.com/SETI/rms-metadata-tools.git
    cd rms-metadata-tools
    "${VENV_DIR}/bin/pip" install ".[cloud]"
fi
export PATH="${VENV_DIR}/bin:$PATH"
