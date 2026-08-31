################################################################################
# cumulative_support.py - Code for cumulative index files
################################################################################
"""Tools for concatenating per-volume tables into cumulative tables."""
import argparse
import fnmatch
from pathlib import Path
from typing import cast

from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.geometry_support as geom
import metadata_tools.index_support as idx
import metadata_tools.label_support as lab
import metadata_tools.util as util
from metadata_tools.config import get_host_config


#===============================================================================
def _cat_rows(volume_tree: FCPath,
              cumulative_dir: FCPath,
              template_path: str | Path | FCPath,
              volume_glob: str,
              table: com.Table,
              *,
              exclude: list[str] | None = None,
              volumes: list[str] | None = None) -> None:
    """Concatenate one table type across volumes into a cumulative table and label.

    Parameters:
        volume_tree: Root of the tree containing the volumes.
        cumulative_dir: Directory in which the cumulative files will reside.
        template_path: Path to the host template.
        volume_glob: Glob pattern for volume identification.
        table: Table object.
        exclude: List of volumes to exclude.
        volumes: List of volume ids to process; an explicit list (even empty)
            selects exactly those volumes, while None processes every
            discovered volume.
    """
    logger = com.get_logger()
    hconf = get_host_config()

    table_type = table.qualifier or ''
    if table.level:
        table_type += '_' + table.level
    ext = '.csv' if table_type == 'inventory' else '.tab'

    # Walk the input tree, adding lines for each found volume
    logger.info('Building Cumulative %s table', table_type)
    content: list[str] = []
    cumulative_file = FCPath('')
    for root, dirs, _files in volume_tree.walk(top_down=True):
        # __skip directory will not be scanned, so it's safe for test results
        if '__skip' in root.as_posix():
            continue

        # Ignore cumulative directory
        if cumulative_dir.name in root.as_posix():
            continue

        # Sort directories
        dirs.sort()
        root = FCPath(root)

        # Determine notional volume
        parts = root.parts
        vol = parts[-1]

        # Do not continue if this volume is excluded
        skip = False
        if exclude is not None:
            for item in exclude:
                if item in root.parts:
                    skip = True
        if skip:
            continue

        # Test whether this root is a volume
        if fnmatch.filter([vol], volume_glob):
            # volumes=None means all volumes; an explicit list (even empty) is a filter.
            if volumes is None or vol in volumes:
                if vol != cumulative_dir.name:
                    volume_id = hconf.get_volume_id(root)
                    cumulative_id = hconf.get_volume_id(cumulative_dir)

                    # Read the table file; skip this volume if it has none
                    table_file = root / ('%s_%s' % (vol, table_type) + ext)
                    try:
                        # as_string is False, so the result is a list of lines.
                        lines = cast(list[str], util.read_txt_file(table_file))
                    except FileNotFoundError:
                        continue

                    # Copy table file to cumulative index
                    cumulative_file = \
                        FCPath(table_file.as_posix().replace(volume_id, cumulative_id))
                    content += lines

    # Write table and label
    if content:
        logger.info('Writing cumulative file %s.', cumulative_file)
        util.write_txt_file(cumulative_file, content)

        logger.info('Writing cumulative label.')
        lab.create(cumulative_file, template_path,
                   table_type=table_type.upper(),
                   use_global_template=table.use_global_template)

#===============================================================================
def get_args(host: str | None = None,
             exclude: list[str] | None = None) -> argparse.ArgumentParser:
    """Argument parser for cumulative metadata.

    Parameters:
        host: Host name, e.g. 'GOISS'.
        exclude: List of volumes to exclude.

    Returns:
        Parser containing the argument specifications.
    """

    # Get common args
    parser = com.get_common_args(host=host, volume_arg=None,
                                            metadata_arg=None,
                                            output_arg='output_dir')

    # Add cumulative args
    gr = parser.add_argument_group('Cumulative Arguments')

    gr.add_argument('--exclude', '-e', nargs='*', type=str, metavar='exclude',
                    default=exclude,
                    help='''List of volumes to exclude.''')

    # Return parser
    return parser

#===============================================================================
def create_cumulative_indexes(template_name: str,
                              volumes: list[str] | None = None,
                              args: argparse.Namespace | None = None,
                              exclude: list[str] | None = None) -> None:
    """Create the cumulative files for a collection of volumes.

    Parameters:
        template_name: Name of index template.
        volumes: List of volume ids to process; an explicit list (even empty)
            overrides args.volumes, while None falls back to args.volumes.
        args: Parsed arguments.
        exclude: List of volumes to exclude.
    """
    # Parse arguments
    host, _index_type, template_dir = util.parse_template_name(template_name)
    template_path = template_dir / FCPath(template_name).with_suffix('.lbl')

    if not args:
        parser = get_args(host=host, exclude=exclude)
        args = parser.parse_args()

    # An explicit volumes list, including an empty one, overrides args.volumes.
    if volumes is None:
        volumes = args.volumes

    # A user-supplied --exclude on the command line takes precedence over the
    # exclude= parameter (typically the host's configured default).
    if args.exclude is not None:
        exclude = args.exclude

    cumulative_dir = FCPath(args.output_dir)
    volume_tree = cumulative_dir.parent

    # Set logger
    logger = com.get_logger()
    logger.info('New cumulative indexes for %s.', volume_tree.name)

    # Build volume glob
    volume_glob = util.get_volume_glob(volume_tree.name)

    # Build the cumulative tables
    tables = [
        geom.SkyTable(level='summary'),
        geom.SkyTable(level='detailed'),
        # geom.SunTable(level='summary') would go here; not yet wired in
        # (see geometry_support.tables.SunTable).
        geom.BodyTable(level='summary'),
        geom.BodyTable(level='detailed'),
        geom.RingTable(level='summary'),
        geom.RingTable(level='detailed'),
        geom.InventoryTable(),
        idx.IndexTable(qualifier='supplemental'),
    ]
    for table in tables:
        _cat_rows(volume_tree, cumulative_dir, template_path, volume_glob,
                  table, exclude=exclude, volumes=volumes)

################################################################################
