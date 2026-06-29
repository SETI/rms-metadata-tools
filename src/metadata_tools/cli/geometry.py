"""Single entry point for geometry table generation across all hosts.

Examples:
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -vv GO_0017
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -p *C0349605600R*

The full list of command-line options is documented in the user guide.
"""
import sys

from metadata_tools.cli._host import load_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry HOST_ID [args...]')
    load_host(sys.argv[1])

    import geometry_config as config
    import host_config as hconf
    import host_init  # noqa: F401

    import metadata_tools.geometry_support as geom

    geom.process_tables(hconf.template_name,
                        glob=config.glob,
                        index_glob=config.index_glob,
                        selection=config.selection,
                        exclude=config.exclude)
