"""Single entry point for supplemental index generation across all hosts.

Examples:
    metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \
        $RMS_METADATA_TEST/GO_0xxx/
    metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \
        $RMS_METADATA_TEST/GO_0xxx/ --volumes GO_0022

The full list of command-line options is documented in the user guide.
"""
import sys

from metadata_tools.cli._host import load_host
from metadata_tools.config import get_host_config, get_index_config, set_host


def main() -> None:
    """Entry point for the ``metadata-index`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index HOST_ID [args...]')
    host_id = sys.argv[1]
    load_host(host_id)
    set_host(host_id)
    hconf = get_host_config()
    config = get_index_config()

    import metadata_tools.index_support as idx

    idx.process_index(hconf.template_name, glob=config.glob)
