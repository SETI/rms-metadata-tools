"""Local worker entry point for geometry table generation across all hosts.

This is the rms-cloud-tasks worker counterpart of ``metadata-geometry``: the same work,
distributed across local Worker processes. Basic usage matches ``metadata-geometry``;
all cloud_tasks Worker arguments are also accepted.

GCP VMs launched by ``metadata-geometry-cloud`` invoke this entry point via the startup
script. For local parallelism without GCP, use this command directly:

  metadata-geometry-worker GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \\
      --volumes GO_0022 GO_0016 --num-simultaneous-tasks 12
  metadata-geometry-worker COISS_xxxx $RMS_METADATA/COISS_2xxx/ \\
      $RMS_METADATA_TEST/COISS_2xxx/ --volumes COISS_2001 COISS_2002 \\
      --num-simultaneous-tasks 12

Command-line arguments:

  HOST_ID                     Host directory, e.g. GO_0xxx or COISS_xxxx. It must
                              come first.
  metadata_tree               Top of the tree holding the volumes' index files.
  output_tree                 Top of the tree in which the geometry tables are
                              written. For hosts with an index stage, it holds the
                              supplemental index files.
  --volumes [VOLUME ...]      Process only these volumes. This disables --new_only.
  --exclude, -e [VOLUME ...]  Skip these volumes. The default is the host's
                              configured list or, failing that, the collection's
                              cumulative volume.
  --new_only, -n              Skip volumes that already contain an *_inventory.csv.
  --first, -f N               Process at most N files in each volume.
  --pattern, -p PATTERN       Process only the files whose path matches this glob
                              pattern.
  --labels, -l                Write labels for existing tables; compute no geometry.
  --sampling, -s N            Pixel sampling density of the field-of-view meshgrid
                              (default 8).
  --body-samples, -b N        Minimum number of samples across the bounding box of
                              each body (default 16).
  --no-body-meshgrids         Sample every body on the field-of-view meshgrid rather
                              than on a meshgrid of its own.
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
)
from metadata_tools.config import get_exclude, get_host_config, get_index_glob, set_host


class _GeometryTask:
    """Picklable callable passed to Worker; safe to use with multiprocessing spawn."""

    def __init__(self, host_id: str, template_name: str, glob: str | None,
                 index_glob: str | None,
                 exclude: list[str] | None) -> None:
        """Store the task configuration.

        Parameters:
            host_id: The host identifier (e.g. ``'GO_0xxx'``).
            template_name: The host's label template name.
            glob: Filename glob for selecting PDS labels, or None for the default.
            index_glob: Filename glob for locating index label files, or None for
                the default.
            exclude: Volume IDs to exclude from processing, or None.
        """
        self._host_id = host_id
        self._template_name = template_name
        self._glob = glob
        self._index_glob = index_glob
        self._exclude = exclude

    def __call__(self, _task_id: str, task_data: dict[str, Any],
                 worker_data: Any) -> tuple[bool, Any]:
        """Generate the geometry tables for one volume.

        Parameters:
            _task_id: The cloud_tasks task ID (unused).
            task_data: Task payload; ``task_data['volume_id']`` names the volume
                to process.
            worker_data: Worker context providing the parsed command-line ``args``.

        Returns:
            A ``(retry, result)`` tuple; always ``(False, None)``.
        """
        set_host(self._host_id)
        from copy import copy

        from filecache import FileCache

        from metadata_tools.geometry_support import process_tables

        # Private auto-deleting cache reclaims downloaded index files per task; the
        # global cache never evicts on single-instance GCP runs, exhausting the boot disk.
        with FileCache(cache_name=None, delete_on_exit=True) as fc:
            args = copy(worker_data.args)
            args.metadata_tree = fc.new_path(args.metadata_tree)
            process_tables(self._template_name,
                           glob=self._glob,
                           index_glob=self._index_glob,
                           exclude=self._exclude,
                           args=args,
                           volumes=[task_data['volume_id']])
        return False, None


def main() -> None:
    """Entry point for the ``metadata-geometry-worker`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry-worker HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))

    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.util as util
    from metadata_tools.geometry_support import get_args

    host, _, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host, exclude=get_exclude())

    run_cloud_worker(parser, _GeometryTask(host_id, hconf.template_name,
                                           hconf.glob, get_index_glob(),
                                           get_exclude()))
