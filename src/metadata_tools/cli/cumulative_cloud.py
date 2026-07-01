"""Single cloud entry point for cumulative table generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-cumulative``: the same work,
distributed across workers. GCP runs are not yet working. For local runs the basic usage
matches ``metadata-cumulative``, and all cloud_tasks arguments are also accepted.

Examples:
 For local runs, the basic usage is identical to metadata-cumulative. In addition, all
 cloud_tasks arguments are also accepted. Bare filenames for --config and --task-file are
 resolved relative to the installed host directory, so the command can be run from any directory:

   metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/ --task-file cumulative_tasks.json
   metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/ --task-file cumulative_tasks.json -vv GO_0017

 For GCP runs, use:
   gcloud auth application-default login       # if necessary

   metadata-cumulative-cloud GO_0xxx --config gcp_cumulative_config.yml --task-file cumulative_tasks.json --use-spot

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
from typing import Any

from metadata_tools.cli._host import dispatch_cloud_run_if_config, load_host, resolve_host_paths


class _CumulativeTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str) -> None:
        self._host_id = host_id
        self._template_name = template_name

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        load_host(self._host_id)
        import geometry_config  # noqa: F401  (side effects: column registration)

        from metadata_tools.cumulative_support import create_cumulative_indexes
        create_cumulative_indexes(self._template_name, args=worker_data.args)
        return False, None


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir)
    dispatch_cloud_run_if_config()

    import geometry_config  # noqa: F401  (side effects: column registration)
    import host_config as hconf
    from cloud_tasks.worker import Worker

    import metadata_tools.util as util
    from metadata_tools.cumulative_support import get_args

    async def _run() -> None:
        host, _, _ = util.parse_template_name(hconf.template_name)
        parser = get_args(host=host)
        worker = Worker(_CumulativeTask(host_id, hconf.template_name),
                        args=sys.argv[1:],
                        argparser=parser)
        await worker.start()

    asyncio.run(_run())
