"""GCP dispatch entry point for supplemental index generation across all hosts.

Dispatches index generation to GCP via rms-cloud-tasks.  Requires ``--config``
pointing at a GCP cloud_tasks config YAML; use ``metadata-index-worker`` for
local parallel runs.

First generate a task file:

  metadata-task-list GO_0xxx $RMS_VOLUMES_GCP/GO_0xxx/ --output tasks.json

Then dispatch:

  metadata-index-cloud GO_0xxx $RMS_VOLUMES_GCP/GO_0xxx/ $RMS_METADATA_GCP/GO_0xxx/ \\
      $RMS_METADATA_TEST_GCP/GO_0xxx/ --use-spot \\
      --config cloud/GO_0xxx/gcp_index_config.yml --task-file cloud/GO_0xxx/tasks.json

Or dispatch directly from a volume list (task file is generated automatically):

  metadata-index-cloud GO_0xxx $RMS_VOLUMES_GCP/GO_0xxx/ $RMS_METADATA_GCP/GO_0xxx/ \\
      $RMS_METADATA_TEST_GCP/GO_0xxx/ --use-spot \\
      --config cloud/GO_0xxx/gcp_index_config.yml --volumes GO_0022 GO_0016

The full list of command-line options is documented in the user guide.
"""
import sys

from metadata_tools.cli._host import (
    cloud_dir_for,
    dispatch_cloud_run_if_config,
    load_host,
    resolve_host_paths,
    volumes_as_task_file,
)
from metadata_tools.config import get_host_config, set_host


def main() -> None:
    """Entry point for the ``metadata-index-cloud`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))

    if '--config' not in sys.argv:
        sys.exit('metadata-index-cloud requires --config; use metadata-index-worker for local runs')

    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.util as util
    from metadata_tools.index_support import get_args

    host, index_type, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, index_type=index_type)

    with volumes_as_task_file():
        rc = dispatch_cloud_run_if_config(host_id, parser,
                                          worker_cmd_name='metadata-index-worker')
    sys.exit(rc)
