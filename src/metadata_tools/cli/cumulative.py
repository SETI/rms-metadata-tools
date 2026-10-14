"""Single entry point for cumulative table generation across all hosts.

Examples:
    metadata-cumulative GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/
    metadata-cumulative GO_0xxx $RMS_METADATA/GO_0xxx/GO_0999/ --volumes GO_0022

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

The user guide describes the options in more detail.
"""
import sys

from metadata_tools.cli._host import load_host
from metadata_tools.config import get_exclude, get_host_config, set_host


def main() -> None:
    """Entry point for the ``metadata-cumulative`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative HOST_ID [args...]')
    host_id = sys.argv[1]
    load_host(host_id)
    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.cumulative_support as cml

    cml.create_cumulative_indexes(hconf.template_name, exclude=get_exclude())
