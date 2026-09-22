#!/usr/bin/env bash
#
# rms-metadata-tools - GCP VM Image Build Script
#
# Bakes a Compute Engine image with the metadata-tools worker environment
# preinstalled (python3, git, and a /root/venv holding
# rms-metadata-tools[cloud]) so cloud-dispatch instances skip the
# apt-get/pip work in cloud/gcp_common_startup.sh. The image is published
# into the "metadata-tools" image family; the cloud configs reference the
# family name, so each rebuild rotates the fleet onto the new image with
# no config edits. The startup script runs an upgrade-if-needed check
# against PyPI on every boot, so a stale image still runs the current
# release; rebuilding after a release is an optimization, not required.
#
# The builder VM runs the bake as its startup script and powers itself
# off on success; a stopped instance is the completion signal. No SSH is
# involved. On timeout or bake failure the serial-port log is saved for
# diagnosis and the builder is deleted.
#
# Usage:
#   ./scripts/build-gcp-image.sh [VERSION]
#
#   VERSION  Optional rms-metadata-tools release to install (e.g. 1.2.3).
#            Defaults to the latest release on PyPI.
#
# Options (environment variables):
#   PROJECT  GCP project id        (default: rms-metadata)
#   ZONE     Builder VM zone       (default: us-central1-a)
#   FAMILY   Target image family   (default: metadata-tools)

set -euo pipefail

PROJECT="${PROJECT:-rms-metadata}"
ZONE="${ZONE:-us-central1-a}"
FAMILY="${FAMILY:-metadata-tools}"
VERSION="${1:-}"

TIMEOUT_SECS=600            # 10 minutes; a normal bake finishes well under this
POLL_SECS=20

BUILDER="metadata-img-builder-$(date +%s)"
IMAGE="${FAMILY}-$(date +%Y%m%d-%H%M)"

if [ -n "$VERSION" ]; then
    PIP_SPEC="rms-metadata-tools[cloud]==${VERSION}"
else
    PIP_SPEC="rms-metadata-tools[cloud]"
fi

BAKE_SCRIPT="$(mktemp)"
trap 'rm -f "$BAKE_SCRIPT"' EXIT

# The bake runs unattended as the instance startup script; poweroff at the
# end is the success signal the poll loop below waits for. A failed step
# aborts before poweroff, leaving the instance RUNNING until the timeout.
cat > "$BAKE_SCRIPT" <<EOF
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git
cd /root
python3 -m venv venv
/root/venv/bin/pip install "${PIP_SPEC}"
apt-get clean
echo "BAKE COMPLETE"
poweroff
EOF

echo "Building image ${IMAGE} (family ${FAMILY}) from ${PIP_SPEC}"
echo "Creating builder VM ${BUILDER} in ${PROJECT}/${ZONE}..."

# The builder disk size becomes the image's MINIMUM boot disk size; keep it
# at the stock Ubuntu image's 10 GB so any config's disk sizing is accepted.
gcloud compute instances create "$BUILDER" \
    --project="$PROJECT" --zone="$ZONE" \
    --machine-type=e2-standard-2 \
    --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
    --boot-disk-type=pd-balanced --boot-disk-size=10GB \
    --metadata-from-file=startup-script="$BAKE_SCRIPT"

cleanup_builder() {
    echo "Deleting builder VM ${BUILDER}..."
    gcloud compute instances delete "$BUILDER" \
        --project="$PROJECT" --zone="$ZONE" --quiet || true
}

save_serial_log() {
    local log="/tmp/${BUILDER}-serial.log"
    gcloud compute instances get-serial-port-output "$BUILDER" \
        --project="$PROJECT" --zone="$ZONE" > "$log" 2>/dev/null || true
    echo "Serial-port log saved to ${log}"
}

echo "Waiting for bake to finish (timeout ${TIMEOUT_SECS}s)..."
elapsed=0
while true; do
    status="$(gcloud compute instances describe "$BUILDER" \
        --project="$PROJECT" --zone="$ZONE" --format='value(status)')"
    if [ "$status" = "TERMINATED" ]; then
        break
    fi
    if [ "$elapsed" -ge "$TIMEOUT_SECS" ]; then
        echo "ERROR: bake did not finish within ${TIMEOUT_SECS}s (status ${status})" >&2
        save_serial_log
        cleanup_builder
        exit 1
    fi
    sleep "$POLL_SECS"
    elapsed=$((elapsed + POLL_SECS))
done
echo "Bake finished after ~${elapsed}s"

echo "Creating image ${IMAGE}..."
gcloud compute images create "$IMAGE" \
    --project="$PROJECT" \
    --source-disk="$BUILDER" --source-disk-zone="$ZONE" \
    --family="$FAMILY" --storage-location=us

cleanup_builder

echo "Done: image ${IMAGE} published in family ${FAMILY}"
