"""GCP dispatch entry point for geometry table generation across all hosts.

Dispatches geometry generation to GCP via rms-cloud-tasks.  Requires ``--config``
pointing at a GCP cloud_tasks config YAML; use ``metadata-geometry-worker`` for
local parallel runs.

First generate a task file:

  metadata-task-list GO_0xxx $RMS_METADATA_GCP/GO_0xxx/ --output tasks.json

Then dispatch:

  metadata-geometry-cloud GO_0xxx $RMS_METADATA_GCP/GO_0xxx/ $RMS_METADATA_TEST_GCP/GO_0xxx/ \\
      --use-spot \\
      --config cloud/GO_0xxx/gcp_geometry_config.yml --task-file cloud/GO_0xxx/tasks.json

Or dispatch directly from a volume list (task file is generated automatically):

  metadata-geometry-cloud GO_0xxx $RMS_METADATA_GCP/GO_0xxx/ \\
      $RMS_METADATA_TEST_GCP/GO_0xxx/ --use-spot \\
      --config cloud/GO_0xxx/gcp_geometry_config.yml --volumes GO_0022 GO_0016

To preview the startup script that would be sent to GCP instances:

  metadata-geometry-cloud GO_0xxx $RMS_METADATA_GCP/GO_0xxx/ \\
      $RMS_METADATA_TEST_GCP/GO_0xxx/ --create-startup-file startup.sh

Use ``--startup-template`` to substitute a custom file for ``gcp_common_startup.sh``:

  metadata-geometry-cloud GO_0xxx ... --config ... --startup-template my_header.sh

The full list of command-line options is documented in the user guide.
"""
import sys
from pathlib import Path

from metadata_tools.cli._host import (
    build_startup_script,
    cloud_dir_for,
    dispatch_cloud_run_if_config,
    load_host,
    resolve_host_paths,
    volumes_as_task_file,
)
from metadata_tools.config import get_geometry_config, get_host_config, set_host

_WORKER = 'metadata-geometry-worker'


def main() -> None:
    """Entry point for the ``metadata-geometry-cloud`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))

    if '--config' not in sys.argv and '--create-startup-file' not in sys.argv:
        sys.exit(
            'metadata-geometry-cloud requires --config; use metadata-geometry-worker for local runs'
        )

    startup_template: str | None = None
    if '--startup-template' in sys.argv:
        idx = sys.argv.index('--startup-template')
        if idx + 1 >= len(sys.argv):
            sys.exit('--startup-template requires a file path argument')
        startup_template = sys.argv[idx + 1]

    set_host(host_id)
    hconf = get_host_config()
    config = get_geometry_config()

    import metadata_tools.util as util
    from metadata_tools.geometry_support import get_args

    host, _, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, selection=config.selection, exclude=config.exclude)

    if '--create-startup-file' in sys.argv:
        idx = sys.argv.index('--create-startup-file')
        if idx + 1 >= len(sys.argv):
            sys.exit('--create-startup-file requires a file path argument')
        Path(sys.argv[idx + 1]).write_text(
            build_startup_script(host_id, parser, _WORKER, startup_template)
        )
        sys.exit(0)

    with volumes_as_task_file():
        rc = dispatch_cloud_run_if_config(host_id, parser, worker_cmd_name=_WORKER,
                                          startup_template=startup_template)
    sys.exit(rc)
