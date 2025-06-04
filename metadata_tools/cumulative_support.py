################################################################################
# cumulative_support.py - Code for cumulative index files
################################################################################
import host_config as hconf
import fnmatch

import metadata_tools as meta
import metadata_tools.util as util
import metadata_tools.label_support as lab
import metadata_tools.geometry_support as geom
import metadata_tools.index_support as idx

from filecache import FCPath

#===============================================================================
def _cat_rows(volume_tree, cumulative_dir, volume_glob, table, *,
              exclude=None, volumes=None):
    """Creates the cumulative files for a collection of volumes.

    Args:
        volume_tree (str, Path, or FCPath): Root of the tree containing the volumes.
        cumulative_dir (str, Path, or FCPath):
            Directory in which the cumulative files will reside.
        volume_glob (str): Glob pattern for volume identification.
        table (geom.Table or idx.Index): Table object.
        exclude (list, optional): List of volumes to exclude.
        volumes (str, optional): If given, only these volumes are processed.
    """
    logger = meta.get_logger()

    table_type = table.qualifier
    if table.level:
        table_type += '_' + table.level
    ext = '.csv' if table_type == 'inventory' else '.tab'

    # Walk the input tree, adding lines for each found volume
    logger.info('Building Cumulative %s table' % table_type)
    content = []
    for root, dirs, files in volume_tree.walk(top_down=True):
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
            if not volumes or vol in volumes:
                if vol != cumulative_dir.name:
                    volume_id = hconf.get_volume_id(root)
                    cumulative_id = hconf.get_volume_id(cumulative_dir)

                    # Check existence of table
                    try:
                        table_file = list(root.glob('%s_%s' % (vol, table_type)+ext))[0]
                    except IndexError:
                        continue

                    # Copy table file to cumulative index
                    cumulative_file = \
                        FCPath(table_file.as_posix().replace(volume_id, cumulative_id))
                    lines = util.read_txt_file(table_file)
                    content += lines

    # Write table and label
    if content:
        logger.info('Writing cumulative file %s.' % cumulative_file)
        util.write_txt_file(cumulative_file, content)

        logger.info('Writing cumulative label.')
        lab.create(cumulative_file,
                   table_type=table_type.upper(),
                   use_global_template=table.use_global_template)

#===============================================================================
def get_args(host=None, exclude=None):
    """Argument parser for cumulative metadata.

    Args:
        host (str): Host name, e.g. 'GOISS'.
        exclude (list, optional): List of volumes to exclude.

     Returns:
        argparser.ArgumentParser :
            Parser containing the argument specifications.
    """

    # Get parser with common args
    parser = meta.get_common_args(host=host)

    # Add parser for index args
    gr = parser.add_argument_group('Cumulative Arguments')
    gr.add_argument('--exclude', '-e', nargs='*', type=str, metavar='exclude',
                    default=exclude,
                    help='''List of volumes to exclude.''')

    # Return parser
    return parser

#===============================================================================
def create_cumulative_indexes(template_name, exclude=None):
    """Creates the cumulative files for a collection of volumes.

    Args:
        template_name (str): Name of index template.
        exclude (list, optional): List of volumes to exclude.
    """
    # Parse arguments
    host, index_type = util.parse_template_name(template_name)
    parser = get_args(host=host, exclude=exclude)
    args = parser.parse_args()

    volume_tree = FCPath(args.input_tree)
    cumulative_dir = FCPath(args.output_tree)
    volumes = args.volumes

    # Set logger
    logger = meta.get_logger()
    logger.info('New cumulative indexes for %s.' % volume_tree.name)

    # Build volume glob
    volume_glob = util.get_volume_glob(volume_tree.name)

    # Build the cumulative tables
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              geom.SkyTable(level='summary'),
              exclude=exclude, volumes=volumes)
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              geom.SkyTable(level='detailed'),
              exclude=exclude, volumes=volumes)
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              geom.BodyTable(level='summary'),
              exclude=exclude, volumes=volumes)
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              geom.BodyTable(level='detailed'),
              exclude=exclude, volumes=volumes)
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              geom.RingTable(level='summary'),
              exclude=exclude, volumes=volumes)
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              geom.RingTable(level='detailed'),
              exclude=exclude, volumes=volumes)
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              geom.InventoryTable(),
              exclude=exclude, volumes=volumes)
    _cat_rows(volume_tree, cumulative_dir, volume_glob,
              idx.IndexTable(qualifier='supplemental'),
              exclude=exclude, volumes=volumes)

################################################################################
