"""Single entry point for geometry table generation across all hosts.

Examples:
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \\
        --volumes GO_0022
    metadata-geometry GO_0xxx $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ \\
        -p *C0349605600R*
    metadata-geometry COISS_xxxx $RMS_METADATA/COISS_2xxx/ $RMS_METADATA_TEST/COISS_2xxx/ \\
        --volumes COISS_2001
    metadata-geometry COISS_xxxx $RMS_METADATA/COISS_1xxx/ $RMS_METADATA_TEST/COISS_1xxx/ \\
        --volumes COISS_1001 --first 40

The Cassini ISS host has no index stage, so for COISS_xxxx the output tree must
already contain a directory for each volume to process.

Command-line arguments:

  HOST_ID                     Host directory, e.g. GO_0xxx or COISS_xxxx. It must
                              come first.
  metadata_tree               Top of the tree holding the volumes' index files.
  output_tree                 Top of the tree in which the geometry tables are
                              written. For hosts with an index stage, it holds the
                              supplemental index files.
  --volumes [VOLUME ...]      Process only these volumes. This disables --new_only.
  --exclude, -e [VOLUME ...]  Skip these volumes. The default is the host's
                              configured list or, failing that, the collection's
                              cumulative volume.
  --new_only, -n              Skip volumes that already contain an *_inventory.csv.
  --first, -f N               Process at most N files in each volume.
  --pattern, -p PATTERN       Process only the files whose path matches this glob
                              pattern.
  --labels, -l                Write labels for existing tables; compute no geometry.
  --sampling, -s N            Pixel sampling density of the field-of-view meshgrid
                              (default 8).
  --body-samples, -b N        Minimum number of samples across the bounding box of
                              each body (default 16).
  --no-body-meshgrids         Sample every body on the field-of-view meshgrid rather
                              than on a meshgrid of its own.
  --help, -h                  Print a summary of the arguments and exit.

The user guide describes the options in more detail.
"""
import sys

from metadata_tools.cli._host import load_host
from metadata_tools.config import get_exclude, get_host_config, get_index_glob, set_host


def main() -> None:
    """Entry point for the ``metadata-geometry`` console script."""
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit('Usage: metadata-geometry HOST_ID [args...]')
    host_id = sys.argv[1]
    load_host(host_id)
    set_host(host_id)
    hconf = get_host_config()

    import metadata_tools.geometry_support as geom

    geom.process_tables(hconf.template_name,
                        glob=hconf.glob,
                        index_glob=get_index_glob(),
                        exclude=get_exclude())
