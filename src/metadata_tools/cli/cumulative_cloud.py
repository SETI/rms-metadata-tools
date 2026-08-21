"""GCP dispatch entry point for cumulative table generation across all hosts.

Dispatches cumulative generation to GCP via rms-cloud-tasks.  ``--config`` names a GCP
cloud_tasks config YAML, defaulting to ``cloud/<HOST>/gcp_cumulative_config.yml`` when that
file exists; use
``metadata-cumulative-worker`` for local runs.

  gcloud auth application-default login       # if necessary

  metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST_GCP/GO_0xxx/GO_0999/ \\
      --use-spot --config cloud/GO_0xxx/gcp_cumulative_config.yml

To preview the startup script that would be sent to the GCP instance:

  metadata-cumulative-cloud GO_0xxx $RMS_METADATA_TEST_GCP/GO_0xxx/GO_0999/ \\
      --create-startup-file startup.sh

Optional overrides (all consumed before dispatch; do not reach cloud_tasks or the worker):
  --startup-template <file>   Use <file> instead of cloud/gcp_common_startup.sh.
  --oops-resources <name>     Persistent disk name for OOPS resources.
  --service-account <account> GCP service account (overrides $GCP_SERVICE_ACCOUNT).
  --debug-branch <branch>     Git branch to clone on GCP VMs (overrides $GCP_DEBUG_BRANCH).
  --ssh-paste                 With --create-startup-file: replace ``cd /root`` with ``cd ~``
                              so the script can be pasted into an SSH terminal as a non-root user.

The full list of command-line options is documented in the user guide.
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
        sys.exit(f'metadata-cumulative-cloud requires --config (default {default_config} not '
                 'found); use metadata-cumulative-worker for local runs')

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
