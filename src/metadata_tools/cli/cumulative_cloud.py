"""Single cloud entry point for cumulative table generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-cumulative``: the same work,
distributed across workers. GCP runs are not yet working. For local runs the basic usage
matches ``metadata-cumulative``, and all cloud_tasks arguments are also accepted.

Examples:
 For local runs, the basic usage is identical to metadata-cumulative. In addition, all
 cloud_tasks arguments are also accepted. Bare filenames for --config are resolved relative
 to the installed host directory, so the command can be run from any directory:

   metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/
   metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/ --volumes GO_0017

 For GCP runs, use:
   gcloud auth application-default login       # if necessary

   metadata-cumulative-cloud GO_0xxx --use-spot --config cloud/GO_0xxx/gcp_cumulative_config.yml

The full list of command-line options is documented in the user guide.
"""
import sys
from typing import Any

from metadata_tools.cli._host import (
    cloud_dir_for,
    dispatch_cloud_run_if_config,
    load_host,
    resolve_host_paths,
    run_cloud_worker,
    single_task_as_task_file,
)
from metadata_tools.config import get_host_config, set_host


class _CumulativeTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str) -> None:
        self._host_id = host_id
        self._template_name = template_name

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        set_host(self._host_id)  # also registers geometry_config: column registration

        from metadata_tools.cumulative_support import create_cumulative_indexes
        create_cumulative_indexes(self._template_name, args=worker_data.args)
        return False, None


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))
    with single_task_as_task_file():
        rc = dispatch_cloud_run_if_config()
        if rc is not None:
            sys.exit(rc)

        set_host(host_id)  # also registers geometry_config: column registration
        hconf = get_host_config()

        import metadata_tools.util as util
        from metadata_tools.cumulative_support import get_args

        host, _, _ = util.parse_template_name(hconf.template_name)
        parser = get_args(host=host)
        run_cloud_worker(parser, _CumulativeTask(host_id, hconf.template_name),
                         supports_volumes=False)
