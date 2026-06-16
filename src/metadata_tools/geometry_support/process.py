################################################################################
# geometry_support/process.py - Entry points for geometry table generation.
################################################################################
import argparse
import fnmatch

from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.util as util
from metadata_tools.geometry_support.suite import Suite


#===============================================================================
def get_args(host: str | None = None, selection: str | None = None,
             exclude: list[str] | None = None,
             sampling: int = 8) -> argparse.ArgumentParser:
    """Argument parser for geometric metadata.

    Args:
        host: Host name, e.g. 'GOISS'.
        selection:
            A string containing...
            "S" to generate summary files;
            "D" to generate detailed files.
        exclude: List of volumes to exclude.
        sampling: Pixel sampling density.

     Returns:
        Parser containing the argument specifications.
    """

    # Get common args
    parser = com.get_common_args(host=host, volume_arg=None)

    # Add geometry args
    gr = parser.add_argument_group('Geometry Arguments')
    gr.add_argument('--selection', type=str, metavar='selection',
                    default=selection,
                    help='''A string containing:
                             "S" to generate summary files;
                             "D" to generate detailed files.''')
    gr.add_argument('--exclude', '-e', nargs='*', type=str, metavar='exclude',
                    default=exclude,
                    help='''List of volumes to exclude.''')
    gr.add_argument('--new_only', '-n', nargs='*', type=str, metavar='new_only',
                    default=False,
                    help='''Only volumes that contain no output files are processed.''')
    gr.add_argument('--first', '-f', type=int, metavar='first',
                    help='''If given, at most this many input files are processed
                            in each volume.''')
    gr.add_argument('--sampling', '-s', type=int, metavar='sampling',
                    default=sampling,
                    help='''Pixel sampling density.''')

    # Return parser
    return parser

#===============================================================================
def process_tables(template_name: str,
                   volumes: list[str] | None = None,
                   selection: str | None = None,
                   exclude: list[str] | None = None,
                   sampling: int = 8,
                   glob: str | None = None,
                   index_glob: str | None = None,
                   args: argparse.Namespace | None = None,
                   task_file: str | None = None,
                   task_list_only: bool = False) -> None:
    """Create geometry tables for a collection of volumes.

    Args:
        template_name: Name of index template.
        volumes: List of volume ids to process. Overrides args.volumes.
        selection:
            A string containing...
            "S" to generate summary files;
            "D" to generate detailed files.
        exclude: List of volumes to exclude.
        sampling: Pixel sampling density.
        glob: Glob pattern for data files.
        index_glob: Glob pattern for index files.
        args: Parsed arguments.
        task_file:
            Name of tasks file. This file is overwritten. If not given, tasks are provided
            via the task_source generator.
        task_list_only:
            If True, a task list is created and no processing is performed. If task_file is
            given, then the task list is written to that file. Otherwise, the task list is
            accessed via the task_source generator.
    """

    # Parse arguments
    host, _index_type, template_dir = util.parse_template_name(template_name)
    template_path = template_dir / FCPath(template_name).with_suffix('.lbl')
    if args is None:
        parser = get_args(host=host, selection=selection, exclude=exclude, sampling=sampling)
        args = parser.parse_args()

    metadata_tree = FCPath(args.metadata_tree)
    output_tree = FCPath(args.output_tree)
    new_only = args.new_only is not False
    labels_only = args.labels is not False

    if volumes is None:
        volumes = args.volumes

    if volumes:
        new_only = False

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
                if new_only and (list(outdir.glob('*_inventory.csv')) != []):
                    continue

                # Update the task file...
                if task_list_only:
                    com.add_task(vol, 'geometry')

                # ... or process this volume
                else:
                    suite = Suite(indir, outdir, template_path, metadata_dir,
                                  selection=args.selection, glob=glob, index_glob=index_glob,
                                  first=args.first, sampling=args.sampling)
                    suite.create(labels_only=labels_only, pattern=args.pattern)

    # Write the task file
    if task_list_only:
        com.write_task_file(task_file)
