"""Single entry point for cumulative table generation across all hosts.

Examples:
    metadata-cumulative GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/
    metadata-cumulative GO_0xxx $RMS_METADATA/GO_0xxx/GO_0999/ --volumes GO_0022

The full list of command-line options is documented in the user guide.
"""
import sys

from metadata_tools.cli._host import load_host
from metadata_tools.config import get_geometry_config, get_host_config, set_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative HOST_ID [args...]')
    host_id = sys.argv[1]
    load_host(host_id)
    set_host(host_id)
    hconf = get_host_config()
    config = get_geometry_config()

    import metadata_tools.cumulative_support as cml

    cml.create_cumulative_indexes(hconf.template_name, exclude=config.exclude)
