"""Single entry point for supplemental index generation across all hosts.

Examples:
    metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \\
        $RMS_METADATA_TEST/GO_0xxx/
    metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \\
        $RMS_METADATA_TEST/GO_0xxx/ --volumes GO_0022

Command-line arguments:

  HOST_ID                     Host directory, e.g. GO_0xxx or COISS_xxxx. It must
                              come first.
  volume_tree                 Top of the tree holding the volumes' data labels.
  metadata_tree               Top of the tree holding the volumes' index files.
  output_tree                 Top of the tree in which to write the new index files.
  --volumes [VOLUME ...]      Process only these volumes.
  --pattern, -p PATTERN       Process only the files matching this glob pattern.
  --labels, -l                Write labels for existing index files; create no files.
  --type, -t TYPE             Type of index file to create. The default comes from
                              the host's template name, e.g. "supplemental".
  --help, -h                  Print a summary of the arguments and exit.

The user guide describes the options in more detail.
"""
import sys

from metadata_tools.cli._host import load_host
from metadata_tools.config import get_host_config, set_host


def main() -> None:
    """Entry point for the ``metadata-index`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index HOST_ID [args...]')
    host_id = sys.argv[1]
    load_host(host_id)
    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.index_support as idx

    idx.process_index(hconf.template_name, glob=hconf.glob)
