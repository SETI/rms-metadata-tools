"""GCP dispatch entry point for cumulative table generation across all hosts.

Dispatches cumulative generation to GCP via rms-cloud-tasks; use
``metadata-cumulative-worker`` for local runs.

``--config`` defaults to ``cloud/<HOST>/gcp_cumulative_config.yml`` when that file
exists (bare filenames resolve against ``cloud/<HOST>/``); no ``--task-file`` is
needed, since the single cumulative task is generated automatically.

  gcloud auth application-default login       # if necessary

  metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST_GCP/GO_0xxx/GO_0999/ --use-spot

Instance software -- scratch install vs. a stored image:

  By default each instance boots a stock OS image and the startup script installs
  everything from scratch: apt python/git, then a fresh venv with
  ``pip install rms-metadata-tools[cloud]`` (or a git clone under --debug-branch).
  No extra flags are needed.

  To boot instances from a stored GCP image instead -- one baked with the OS
  packages and venv preinstalled -- pass cloud_tasks' ``--image`` with an image
  family name (the family's latest image is used, so a rebaked image is picked up
  without touching any config) or a full image URI:

    metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST_GCP/GO_0xxx/GO_0999/ \\
        --use-spot --image metadata-tools-worker

  The same choice can be stored per stage in the config YAML's provider section:

    gcp:
      image: metadata-tools-worker

  The startup script still runs on a stored image; its install steps largely
  reduce to no-ops against the preinstalled software. Pair with
  --startup-template to skip installation altogether.

To preview the startup script that would be sent to the GCP instance:

  metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST_GCP/GO_0xxx/GO_0999/ \\
      --create-startup-file startup.sh

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

Dispatch arguments, which are not passed to the workers:

  --config FILE               cloud_tasks configuration. The default is
                              cloud/<HOST>/gcp_cumulative_config.yml, if it exists.
  --create-startup-file FILE  Write the instances' startup script to FILE and exit
                              without dispatching.
  --startup-template FILE     Build the startup script from FILE instead of the
                              packaged template.
  --oops-resources NAME       Persistent disk holding the OOPS resources.
  --service-account ACCOUNT   GCP service account (overrides $GCP_SERVICE_ACCOUNT).
  --debug-branch BRANCH       Git branch to clone on the instances (overrides
                              $GCP_DEBUG_BRANCH).
  --ssh-paste                 With --create-startup-file, replace ``cd /root`` with
                              ``cd ~`` so the script can be pasted into an SSH
                              terminal as a non-root user.

All other ``cloud_tasks run`` arguments are also accepted and passed to it, for
example --use-spot, --image, --max-instances and --continue; ``cloud_tasks run
--help`` lists them all.

The user guide describes the options in more detail.
"""
import sys
from pathlib import Path

from metadata_tools.cli._host import (
    build_startup_script,
    cloud_dir_for,
    default_config_arg,
    dispatch_cloud_run_if_config,
    load_host,
    pop_argv_bool_flag,
    pop_argv_flag,
    resolve_host_paths,
    single_task_as_task_file,
)
from metadata_tools.config import get_host_config, set_host

_WORKER = 'metadata-cumulative-worker'


def main() -> None:
    """Entry point for the ``metadata-cumulative-cloud`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative-cloud HOST_ID [args...]')
    host_id = sys.argv[1]
    host_dir = load_host(host_id)
    resolve_host_paths(host_dir, cloud_dir_for(host_id))
    default_config = default_config_arg(host_id, 'cumulative')

    create_startup_file = pop_argv_flag('--create-startup-file')
    startup_template = pop_argv_flag('--startup-template')
    oops_resources = pop_argv_flag('--oops-resources')
    service_account = pop_argv_flag('--service-account')
    debug_branch = pop_argv_flag('--debug-branch')
    ssh_paste = pop_argv_bool_flag('--ssh-paste')

    if '--config' not in sys.argv and create_startup_file is None:
        sys.exit(f'metadata-cumulative-cloud requires --config (no default config at '
                 f'{default_config}; defaults exist only in a source checkout); '
                 'use metadata-cumulative-worker for local runs')

    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.util as util
    from metadata_tools.cumulative_support import get_args

    host, _, _ = util.parse_template_name(hconf.template_name)
    parser = get_args(host=host)

    if create_startup_file is not None:
        Path(create_startup_file).write_text(
            build_startup_script(host_id, parser, _WORKER, startup_template, oops_resources,
                                 debug_branch, for_ssh=ssh_paste),
            encoding='utf-8',
        )
        sys.exit(0)

    with single_task_as_task_file():
        rc = dispatch_cloud_run_if_config(host_id, parser, worker_cmd_name=_WORKER,
                                          startup_template=startup_template,
                                          oops_resources=oops_resources,
                                          service_account=service_account,
                                          debug_branch=debug_branch)
    sys.exit(rc)
