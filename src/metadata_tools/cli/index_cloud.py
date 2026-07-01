"""Single cloud entry point for supplemental index generation across all hosts.

This is the rms-cloud-tasks (GCP) counterpart of ``metadata-index``: the same work,
distributed across workers. For local runs the basic usage matches ``metadata-index``,
and all cloud_tasks arguments are also accepted.

Examples:
 For local runs with explicit volumes via the task source:

   metadata-index-cloud GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \\
       $RMS_METADATA_TEST/GO_0xxx/ --volumes GO_0017 GO_0018 --num-simultaneous-tasks 12

 For GCP runs, first generate a task file:

   metadata-task-list GO_0xxx $RMS_VOLUMES/GO_0xxx/ --output index_tasks.json

 Then dispatch:

   metadata-index-cloud GO_0xxx --config gcp_index_config.yml \\
       --task-file index_tasks.json --use-spot

 Or dispatch directly from a volume list (task file is generated automatically):

   metadata-index-cloud GO_0xxx --config gcp_index_config.yml --volumes GO_0017 GO_0018

The full list of command-line options is documented in the user guide.
"""
import asyncio
import sys
import tempfile
from collections.abc import Iterator
from typing import Any

from metadata_tools.cli._host import dispatch_cloud_run_if_config, load_host, resolve_host_paths


class _IndexTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str, glob: str | None) -> None:
        self._host_id = host_id
        self._template_name = template_name
        self._glob = glob

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        load_host(self._host_id)
        from metadata_tools.index_support import process_index
        process_index(self._template_name, glob=self._glob,
                      args=worker_data.args, volumes=[task_data['volume_id']])
        return False, None


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir)

    # When --volumes is combined with --config (GCP dispatch), cloud_tasks run
    # does not understand --volumes. Materialise the volume list into a temp task
    # file and substitute --task-file so dispatch proceeds normally.
    if '--volumes' in sys.argv and '--config' in sys.argv:
        from metadata_tools import task_list_support as tl
        idx = sys.argv.index('--volumes')
        vols = [v for v in sys.argv[idx + 1:] if not v.startswith('-')]
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as tmp:
            tmp_name = tmp.name
        tl.write_task_file(vols, tmp_name)
        sys.argv = [a for a in sys.argv if a not in (['--volumes'] + vols)]
        sys.argv += ['--task-file', tmp_name]

    dispatch_cloud_run_if_config()

    import host_config as hconf
    import index_config as config
    from cloud_tasks.worker import Worker

    import metadata_tools.util as util
    from metadata_tools.index_support import get_args

    async def _run() -> None:
        host, index_type, _ = util.parse_template_name(hconf.template_name)
        parser = get_args(host=host, index_type=index_type)

        # Pre-parse to read --volumes before Worker construction.
        pre_args, _ = parser.parse_known_args(sys.argv[1:])

        task_src = None
        if pre_args.volumes:
            from metadata_tools import task_list_support as tl
            tasks = list(tl.task_generator(pre_args.volumes))

            def task_src() -> Iterator[dict[str, Any]]:
                return iter(tasks)

        worker = Worker(_IndexTask(host_id, hconf.template_name, config.glob),
                        task_source=task_src,
                        args=sys.argv[1:],
                        argparser=parser)
        await worker.start()

    asyncio.run(_run())
