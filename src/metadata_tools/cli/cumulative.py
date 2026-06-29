"""Single entry point for cumulative table generation across all hosts.

Examples:
    metadata-cumulative GO_0xxx $RMS_METADATA_TEST/GO_0xxx/GO_0999/
    metadata-cumulative GO_0xxx $RMS_METADATA/GO_0xxx/GO_0999/ -vv GO_0017

The full list of command-line options is documented in the user guide.
"""
import sys

from metadata_tools.cli._host import load_host


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-cumulative HOST_ID [args...]')
    load_host(sys.argv[1])

    import geometry_config as config
    import host_config as hconf

    import metadata_tools.cumulative_support as cml

    cml.create_cumulative_indexes(hconf.template_name, exclude=config.exclude)
