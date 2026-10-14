################################################################################
# geometry_support/process.py - Entry points for geometry table generation.
################################################################################
"""Top-level geometry processing: argument parsing and table pipeline."""
import argparse
import fnmatch

import oops
from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.util as util
from metadata_tools.geometry_support.suite import Suite

# Number of QuickPath and QuickFrame tables oops keeps per path and per frame.
# The tables pay off within an image, but every image is at a new time, so a
# table is almost never reused by another one. With the oops default of 40, a
# 3,745-image Cassini volume grew past 7 GB. With 2, the first 60 images ran at
# the same speed, wrote identical tables, and used 879 MB rather than 1,554 MB.
# Disabling the tables instead made the run 2.6 times slower.
QUICK_CACHE_SIZE = 2


#===============================================================================
def limit_quick_caches(size: int = QUICK_CACHE_SIZE) -> None:
    """Limit the number of interpolation tables oops keeps per path and frame.

    Parameters:
        size: Maximum number of QuickPath tables per path and of QuickFrame
            tables per frame.
    """
    oops.config.QUICK.dictionary['quickpath_cache_size'] = size
    oops.config.QUICK.dictionary['quickframe_cache_size'] = size


#===============================================================================
def get_args(host: str | None = None,
             exclude: list[str] | None = None,
             sampling: int = 8,
             body_samples: int = 16) -> argparse.ArgumentParser:
    """Build the argument parser for geometric metadata.

    Parameters:
        host: Host name, e.g. 'GOISS'.
        exclude: List of volumes to exclude.
        sampling: Pixel sampling density.
        body_samples: Minimum number of samples across the bounding box of a
            body; 0 to disable body-specific meshgrids.

    Returns:
        Parser containing the argument specifications.
    """

    # Get common args
    parser = com.get_common_args(host=host, volume_arg=None)

    # Add geometry args
    gr = parser.add_argument_group('Geometry Arguments')
    gr.add_argument('--exclude', '-e', nargs='*', type=str, metavar='exclude',
                    default=exclude,
                    help='''List of volumes to exclude.''')
    gr.add_argument('--new_only', '-n', action='store_true',
                    help='''Only volumes that contain no output files are processed.''')
    gr.add_argument('--first', '-f', type=int, metavar='first',
                    help='''If given, at most this many input files are processed
                            in each volume.''')
    gr.add_argument('--sampling', '-s', type=int, metavar='sampling',
                    default=sampling,
                    help='''Pixel sampling density.''')
    gr.add_argument('--body-samples', '-b', type=int, metavar='body_samples',
                    default=body_samples,
                    help='''Minimum number of samples across the bounding box of
                            each body, however small it appears.''')
    gr.add_argument('--no-body-meshgrids', action='store_true',
                    help='''Sample every body on the meshgrid of the whole
                            field of view, rather than on a meshgrid of its
                            own.''')

    # Return parser
    return parser

#===============================================================================
def process_tables(template_name: str,
                   volumes: list[str] | None = None,
                   exclude: list[str] | None = None,
                   sampling: int = 8,
                   body_samples: int = 16,
                   glob: str | None = None,
                   index_glob: str | None = None,
                   args: argparse.Namespace | None = None) -> None:
    """Create geometry tables for a collection of volumes.

    Parameters:
        template_name: Name of index template.
        volumes: List of volume ids to process. Overrides args.volumes.
        exclude: List of volumes to exclude.
        sampling: Pixel sampling density.
        body_samples: Minimum number of samples across the bounding box of a
            body; 0 to disable body-specific meshgrids.
        glob: Glob pattern for data files.
        index_glob: Glob pattern for index files.
        args: Parsed arguments.
    """

    # Parse arguments
    host, _index_type, template_dir = util.parse_template_name(template_name)
    template_path = template_dir / FCPath(template_name).with_suffix('.lbl')
    if args is None:
        parser = get_args(host=host, exclude=exclude, sampling=sampling,
                          body_samples=body_samples)
        args = parser.parse_args()

    metadata_tree = FCPath(args.metadata_tree)
    output_tree = FCPath(args.output_tree)
    new_only = args.new_only
    body_samples = 0 if args.no_body_meshgrids else args.body_samples
    labels_only = args.labels

    if volumes is None:
        volumes = args.volumes

    # A user-supplied --exclude on the command line takes precedence over the
    # exclude= parameter (typically the host's configured default).
    if args.exclude is not None:
        exclude = args.exclude

    if volumes:
        new_only = False

    # By default, exclude the tree's cumulative volume
    if exclude is None:
        exclude = [util.get_cumulative_id(output_tree.name)]

    # Keep oops from accumulating interpolation tables across images
    limit_quick_caches()

    # Build volume glob
    vol_glob = util.get_volume_glob(output_tree.name)

    # Walk the volume tree, making indexes for each found volume
    for root, dirs, _files in output_tree.walk():
        # __skip directory will not be scanned, so it's safe for test results
        if '__skip' in root.as_posix():
            continue

        # Sort directories for progress monitoring
        dirs.sort()
        root = FCPath(root)

        # Determine notional collection and volume
        parts = root.parts
        coll = parts[-2]
        vol = parts[-1]

        # Proceed only if this root is a volume
        if fnmatch.filter([vol], vol_glob):
            if not volumes or vol in volumes:

                # Set up input and output directories
                indir = root
                outdir = util.select_dir(output_tree, coll, vol)
                metadata_dir = util.select_dir(metadata_tree, coll, vol)

                # Do not continue if this volume is excluded
                skip = False
                if exclude is not None:
                    for item in exclude:
                        if item in indir.parts:
                            skip = True
                if skip:
                    continue

                # Check whether this volume has already been processed
                if new_only and any(outdir.glob('*_inventory.csv')):
                    continue

                suite = Suite(indir, outdir, template_path, metadata_dir,
                              glob=glob, index_glob=index_glob,
                              first=args.first, sampling=args.sampling,
                              body_samples=body_samples)
                suite.create(labels_only=labels_only, pattern=args.pattern)
