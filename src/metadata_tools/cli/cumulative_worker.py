"""Local worker entry point for cumulative table generation across all hosts.

This is the rms-cloud-tasks worker counterpart of ``metadata-cumulative``: the same work,
run via a cloud_tasks Worker. Basic usage is identical to ``metadata-cumulative``;
all cloud_tasks Worker arguments are also accepted.

GCP VMs launched by ``metadata-cumulative-cloud`` invoke this entry point via the startup
script. For local runs, use this command directly:

  metadata-cumulative-worker GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/
  metadata-cumulative-worker GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/ --volumes GO_0017

Command-line arguments:

  HOST_ID                     Host directory, e.g. GO_0xxx or COISS_xxxx. It must
                              come first.
  output_dir                  The collection's cumulative volume directory, e.g.
                              GO_0xxx/GO_0999/. Its parent holds the per-volume
                              tables to combine.
  --volumes [VOLUME ...]      Combine only these volumes.
  --exclude, -e [VOLUME ...]  Skip these volumes. The default is the host's
                              configured list.
  --labels, -l                Write labels for existing cumulative tables; combine
                              nothing.
  --help, -h                  Print a summary of the arguments and exit.

All rms-cloud-tasks Worker arguments are also accepted, for example
--num-simultaneous-tasks, --task-file, --max-num-tasks and --max-runtime; the
rms-cloud-tasks documentation lists them all. Unless --task-file is given,
--volumes is also the source of the Worker's tasks.

The user guide describes the options in more detail.
"""
import sys
from typing import Any

from metadata_tools.cli._host import (
    cloud_dir_for,
    load_host,
    resolve_host_paths,
    run_cloud_worker,
    single_task_as_task_file,
)
from metadata_tools.config import get_exclude, get_host_config, set_host


class _CumulativeTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str,
                 exclude: list[str] | None) -> None:
        """Store the task configuration.

        Parameters:
            host_id: The host identifier (e.g. ``'GO_0xxx'``).
            template_name: The host's label template name.
            exclude: Volume IDs to exclude from processing, or None.
        """
        self._host_id = host_id
        self._template_name = template_name
        self._exclude = exclude

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        """Generate the cumulative tables for the volume tree.

        Parameters:
            _task_id: The cloud_tasks task ID (unused).
            task_data: Task payload (unused; cumulative runs have a single task).
            worker_data: Worker context providing the parsed command-line ``args``.

        Returns:
            A ``(retry, result)`` tuple; always ``(False, None)``.
        """
        set_host(self._host_id)
        from copy import copy

        from filecache import FileCache

        from metadata_tools.cumulative_support import create_cumulative_indexes

        # Private auto-deleting cache reclaims read tables per task (global cache never
        # evicts); write_text uploads on close so remote output survives cache deletion.
        with FileCache(cache_name=None, delete_on_exit=True) as fc:
            args = copy(worker_data.args)
            args.output_dir = fc.new_path(args.output_dir)
            create_cumulative_indexes(self._template_name, args=args,
                                      exclude=self._exclude)
        return False, None


def main() -> None:
    """Entry point for the ``metadata-cumulative-worker`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative-worker HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))

    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.util as util
    from metadata_tools.cumulative_support import get_args

    host, _, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host)

    with single_task_as_task_file():
        run_cloud_worker(parser,
                         _CumulativeTask(host_id, hconf.template_name, get_exclude()),
                         supports_volumes=False)
