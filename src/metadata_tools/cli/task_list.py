"""Generate a task list file for cloud/Worker metadata runs.

Two modes are supported:

**Scan mode** — HOST_ID and a tree path are given; volumes are discovered by walking
the tree:

    metadata-task-list GO_0xxx $RMS_VOLUMES/GO_0xxx/ --output tasks.json
    metadata-task-list GO_0xxx $RMS_METADATA/GO_0xxx/ --output geo_tasks.json

**Explicit mode** — no HOST_ID; volumes are specified directly:

    metadata-task-list --volumes GO_0001 GO_0002 --output tasks.json
"""
import argparse
import sys

from filecache import FCPath

from metadata_tools.cli._host import load_host
from metadata_tools.task_list_support import scan_volumes, write_task_file


def main() -> None:
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('-'):
        # Scan mode: HOST_ID tree --output FILE
        host_id = sys.argv[1]
        load_host(host_id)  # removes HOST_ID from sys.argv, adds host dir to sys.path

        parser = argparse.ArgumentParser(
            description='Generate a task list file by scanning a volume tree.')
        parser.add_argument('tree', type=str,
                            help='Path to the top of the volume or metadata tree.')
        parser.add_argument('--output', '-o', type=str, required=True,
                            help='Output JSON task list file path.')
        args = parser.parse_args()
        volumes = scan_volumes(FCPath(args.tree))
    else:
        # Explicit mode: --volumes V1 V2 ... --output FILE
        parser = argparse.ArgumentParser(
            description='Generate a task list file from an explicit volume list.')
        parser.add_argument('--volumes', nargs='+', required=True,
                            metavar='volume_id',
                            help='One or more volume IDs to include.')
        parser.add_argument('--output', '-o', type=str, required=True,
                            help='Output JSON task list file path.')
        args = parser.parse_args()
        volumes = args.volumes

    write_task_file(volumes, args.output)
