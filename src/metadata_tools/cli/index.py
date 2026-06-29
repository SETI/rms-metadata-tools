"""Single entry point for supplemental index generation across all hosts.

Examples:
    metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
    metadata-index GO_0xxx $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ \
        $RMS_METADATA_TEST/GO_0xxx/ -vv GO_0017

The full list of command-line options is documented in the user guide.
"""
import sys

from metadata_tools.cli._host import load_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-index HOST_ID [args...]')
    load_host(sys.argv[1])

    import host_config as hconf
    import host_init  # noqa: F401
    import index_config as config

    import metadata_tools.index_support as idx

    idx.process_index(hconf.template_name, glob=config.glob)
