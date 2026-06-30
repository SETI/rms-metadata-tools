################################################################################
# process.py - Process entry points for index file generation.
################################################################################
"""Process entry points for index file generation."""
import argparse
import fnmatch
from pathlib import Path

from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.util as util

from .table import IndexTable


#===============================================================================
def get_args(host: str | None = None,
             index_type: str | None = None) -> argparse.ArgumentParser:
    """Argument parser for index files.

    Parameters:
        host: Host name e.g. 'GOISS'.
        index_type: Qualifying string identifying the type of index file to
            create, e.g., 'supplemental'.

    Returns:
        Parser containing the argument specifications.
    """

    # Get common args
    parser = com.get_common_args(host=host)

    # Add index args
    gr = parser.add_argument_group('Index Arguments')
    gr.add_argument('--type', '-t', type=str, metavar='type',
                    default=index_type,
                    help='''Type of index file to create, e.g.,
                            "supplemental".''')

    # Return parser
    return parser

#===============================================================================
def _create_index(volume_tree: FCPath,
                  output_tree: FCPath,
                  template_path: str | Path | FCPath,
                  metadata_tree: str | Path | FCPath | None = None,
                  volumes: list[str] | None = None,
                  labels_only: bool = False,
                  qualifier: str | None = None,
                  glob: str | None = None,
                  pattern: str | None = None,
                  task_file: str | None = None,
                  task_list_only: bool = False) -> None:
    """Create index files for a collection of volumes.

    Parameters:
        volume_tree: Top of the directory tree containing the volume, specifically
            the labels.
        output_tree: Top of the directory tree in which to write the new index
            files. Corrected index files (e.g., <volume>_index.tab) are assumed to
            reside here unless metadata_tree is given.
        template_path: Path to the host template.
        metadata_tree: Top of the directory tree in which to find the corrected
            index file (e.g., <volume>_index.tab).
        volumes: List of volume ids to process.  Overrides args.volumes.
        labels_only: If True, labels are generated for any existing tables.
        qualifier: Qualifying string identifying the type of index file to create,
            e.g., 'supplemental'.
        glob: Glob pattern for data files.
        pattern: Glob pattern for sub-selecting files to process.
        task_file: Name of tasks file.
        task_list_only: If True, a tasks file is created and no processing is
            performed.
    """
    logger = com.get_logger()

    if metadata_tree is not None:
        metadata_tree = FCPath(metadata_tree)
    else:
        metadata_tree = output_tree

    # Build volume glob
    vol_glob = util.get_volume_glob(volume_tree.name)

    # Accumulate the columns that are unused across every processed volume.
    unused: set[str] | None = None

    # Walk the input tree, making indexes for each found volume
    for root, dirs, _files in volume_tree.walk():
        # __skip directory will not be scanned, so it's safe for test results
        if '__skip' in root.as_posix():
            continue

        # Sort directories for progress monitoring
        dirs.sort()
        root = FCPath(root)

        # Determine notional collection and volume
        parts = root.parts
        col = parts[-2]
        vol = parts[-1]

        # Test whether this root is a volume
        if fnmatch.filter([vol], vol_glob):
            if not volumes or vol in volumes:

                # Determine input and output directories
                indir = root
                outdir = util.select_dir(output_tree, col, vol)
                metadata_dir = util.select_dir(metadata_tree, col, vol)

                # Update the task file...
                if task_list_only:
                    com.add_task(vol, col)

                # ... or process this volume
                else:
                    # Process this volume if possible
                    try:
                        index = IndexTable(indir, outdir, template_path, metadata_dir,
                                       qualifier=qualifier or '', volume_id=vol, glob=glob)
                    except FileNotFoundError:
                        continue

                    index.create(labels_only=labels_only, pattern=pattern)
                    unused = index.unused if not unused else unused & index.unused

    # Write the task file
    if task_list_only:
        com.write_task_file(task_file)

    # Log a warning for any columns that never had non-null values in any volume
    if unused:
        logger.warning('Unused columns: %s', unused)
    logger.close(force=True)

#===============================================================================
def process_index(template_name: str,
                  glob: str | None = None,
                  volumes: list[str] | None = None,
                  args: argparse.Namespace | None = None,
                  task_file: str | None = None,
                  task_list_only: bool = False) -> None:
    """Create index files for a collection of volumes.

    Parameters:
        template_name: Name of input template.
        glob: Glob pattern for data files.
        volumes: List of volume ids to process.  Overrides args.volumes.
        args: Parsed arguments.
        task_file: Name of tasks file. This file is overwritten. If not given,
            tasks are provided via the task_source generator.
        task_list_only: If True, a task list is created and no processing is
            performed. If task_file is given, then the task list is written to that
            file. Otherwise, the task list is accessed via the task_source
            generator.
    """

    # Parse arguments
    host, index_type, template_dir = util.parse_template_name(template_name)

    template_path = template_dir / FCPath(template_name).with_suffix('.lbl')
    if not args:
        parser = get_args(host=host, index_type=index_type)
        args = parser.parse_args()

    if not volumes:
        volumes = args.volumes

    if args.task_output:
        task_list_only = True
        task_file = args.task_output

    # Create the index
    _create_index(FCPath(args.volume_tree), FCPath(args.output_tree), template_path,
                  metadata_tree=args.metadata_tree,
                  volumes=volumes,
                  labels_only=args.labels is not False,
                  qualifier=args.type,
                  glob=glob,
                  pattern=args.pattern,
                  task_file=task_file,
                  task_list_only=task_list_only)
