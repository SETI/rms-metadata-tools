"""Single entry point for geometry table generation across all hosts.

Examples:
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ --volumes GO_0022
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -p *C0349605600R*

The full list of command-line options is documented in the user guide.
"""
import sys

from metadata_tools.cli._host import load_host
from metadata_tools.config import get_geometry_config, get_host_config, set_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry HOST_ID [args...]')
    host_id = sys.argv[1]
    load_host(host_id)
    set_host(host_id)
    hconf = get_host_config()
    config = get_geometry_config()

    import metadata_tools.geometry_support as geom

    geom.process_tables(hconf.template_name,
                        glob=config.glob,
                        index_glob=config.index_glob,
                        selection=config.selection,
                        exclude=config.exclude)
