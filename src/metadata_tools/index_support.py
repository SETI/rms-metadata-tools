################################################################################
# index_support.py - Tools for generating index files
################################################################################
"""Tools for generating supplemental index tables and their PDS3 labels."""
import argparse
import ast
import fnmatch
from pathlib import Path
from typing import Any, cast

import fortranformat as ff
import host_config as hconf
import index_config as config
from filecache import FCPath
from pdsparser import PdsLabel
from pdstemplate.pds3table import Pds3Table

import metadata_tools.common as com
import metadata_tools.util as util


################################################################################
# IndexTable class
################################################################################
class IndexTable(com.Table):
    """Class describing an index table for a single volume."""

    #===========================================================================
    def __init__(self,
                 input_dir: str | Path | FCPath | None = None,
                 output_dir: str | Path | FCPath | None = None,
                 template_path: str | Path | FCPath | None = None,
                 metadata_dir: str | Path | FCPath | None = None,
                 qualifier: str = '',
                 glob: str | None = None,
                 **kwargs: Any) -> None:
        """Constructor for an IndexTable object.

        Parameters:
            input_dir: Directory containing the volume, specifically the data
                labels.
            output_dir: Directory in which to write the new index files.
            template_path: Path to the host template.
            metadata_dir: Directory in which to find the "updated" index file
                (e.g., <volume>_index.tab).
            qualifier: Qualifying string identifying the type of index file to
                create, e.g., 'supplemental'.
            glob: Glob pattern for data files.

        Raises:
            FileNotFoundError: If a primary index is required but its label is
                not found.
        """

        # Initialize table, return if specific paths not given
        super().__init__(output_dir, template_path, level="index", qualifier=qualifier, **kwargs)
        if not input_dir:
            return

        # Save inputs
        self.input_dir = FCPath(input_dir)
        self.output_dir = FCPath(output_dir)
        self.metadata_dir = FCPath(metadata_dir)
        self.glob = glob
        self.usage: dict[str, bool] = {}
        self.unused: set[str] = set()

        # Get volume id
        self.volume_id = hconf.get_volume_id(self.input_dir)

        # Get relevant filenames and paths
        primary_index_name = util.get_index_name(self.input_dir, self.volume_id, '')
        index_name = util.get_index_name(self.input_dir, self.volume_id, qualifier)
        self.index_path = self.metadata_dir/(index_name + '.tab')

        # If the index name is the same as the primary index name,
        # then this is the primary index.
        create_primary = index_name == primary_index_name

        # If there is a primary file, read it and build the file list
        if not create_primary:
            self.primary_index_label_path = self.metadata_dir/(primary_index_name + '.lbl')
            if not self.primary_index_label_path.exists():
                raise FileNotFoundError(f'No primary index for {self.volume_id}')
            self.primary_index_path = self.metadata_dir/(primary_index_name + '.tab')

            table = util.pds_table(self.primary_index_label_path)

            primary_row_dicts = table.dicts_by_row()
            self.files: list[FCPath] = [
                FCPath(primary_row_dict['FILE_SPECIFICATION_NAME'])
                for primary_row_dict in primary_row_dicts]

            for i in range(len(self.files)):
                self.files[i] = self.input_dir/self.files[i].with_suffix('.LBL')

        # Otherwise, build the file list from the directory tree
        else:
            self.files = list(self.input_dir.rglob('*.LBL'))

        # Initialize the logger
        com.init_logger(self.output_dir, 'index')
        logger = com.get_logger()

        s = ' '+qualifier if qualifier else ' primary'
        logger.info('New%s index for %s.', s, self.volume_id)

        # Extract relevant fields from the template
        label_name = util.get_index_name(self.input_dir, self.volume_id, qualifier)
        label_path = self.output_dir / FCPath(label_name + '.lbl')

        # as_string is True, so the result is a single string.
        template = cast(str, util.read_txt_file(cast('str | Path | FCPath', template_path),
                                                as_string=True))
        pds3_table = Pds3Table(label_path, template, validate=False,
                               numbers=True, formats=True)
        self.column_stubs = IndexTable._get_column_values(pds3_table)

    #===========================================================================
    def create(self, labels_only: bool = False, pattern: str | None = None) -> None:
        """Create the index file for a single volume.

        Parameters:
            labels_only: If True, labels are generated for any existing geometry
                tables.
            pattern: Glob pattern for sub-selecting files to process.
        """
        if not hasattr(self, 'files'):
            return

        logger = com.get_logger()

        # Build the index
        n = len(self.files)
        if not labels_only:
            for i in range(n):
                file = self.files[i]
                name = file.name
                root = file.parent

                # Make any sub selection
                if pattern and fnmatch.filter([name], pattern) == []:
                    continue

                # Match the glob pattern
                matches = fnmatch.filter([name], cast(str, self.glob))
                if matches == []:
                    continue
                matched_name = matches[0]

                # Log volume ID and subpath
                subdir = util.get_volume_subdir(root, hconf.get_volume_id(root))
                logger.info('%s %4d/%4d  %s', self.volume_id, i+1, n, subdir/name)

                # Make the index for this file
                self.add(root, matched_name)

            # Flag any unused columns
            for name in self.usage:
                if not self.usage[name]:
                    self.unused.update({name})

        # Write tables and make labels
        self.write(labels_only=labels_only)

    #===========================================================================
    def add(self, root: FCPath, name: str) -> None:
        """Write a single index file entry.

        Parameters:
            root: Top of the directory tree containing the volume.
            name: Name of PDS label.
        """

        # Read the PDS3 label
        path = root/name
        label_dict: dict[str, Any] = PdsLabel.from_file(path).as_dict()

        # Write columns
        first = True
        line = ''
        for column_stub in self.column_stubs:
            if not column_stub:
                continue

            # Add column name to usage dict if not already there
            column_name = column_stub['NAME']
            if column_name not in self.usage:
                self.usage[column_name] = False

            # Get the value
            value = self._index_one_value(column_stub, path, label_dict)

            # Write the value into the index
            if not first:
                line += ","

            fvalue = IndexTable._format_column(column_stub, value)
            line += fvalue

            first = False

        self.rows += [line]

    #===========================================================================
    def _index_one_value(self,
                         column_stub: dict[str, Any],
                         label_path: str | Path | FCPath,
                         label_dict: dict[str, Any]) -> Any:
        """Determine value for one row of one column.

        Parameters:
            column_stub: Column stub dictionary.
            label_path: Path to the PDS label.
            label_dict: Dictionary containing the PDS label fields.

        Returns:
            Determined value.

        Raises:
            ValueError: If the value is None and no null constant is defined for
                the column.
        """
        nullval = column_stub['NULL_CONSTANT']

        # Resolve the key function: a built-in `key__<name>` takes priority over
        # one defined in the index_config module. If neither exists, the value is
        # taken straight from the label. Look the function up explicitly (rather
        # than catching KeyError/AttributeError) so that an error raised *inside*
        # a key function propagates instead of being silently swallowed.
        key = column_stub['NAME']
        fn_name = 'key__' + key.lower()
        fn = globals().get(fn_name)
        if fn is None:
            fn = getattr(config, fn_name, None)

        if fn is not None:
            value = fn(label_path, label_dict)
        else:
            value = label_dict.get(key, nullval)

        # If a key function returned None, insert a NULL value.
        if value is None:
            value = nullval

        # A real check (not an assert, which `python -O` strips): if no null
        # constant is defined, a None value cannot be represented in the table.
        if value is None:
            raise ValueError('Null constant needed for %s.' % column_stub['NAME'])

        # If valid value, mark this column as used
        if value != nullval:
            self.usage[key] = True

        return value

    #===========================================================================
    @staticmethod
    def _get_column_values(pds3_table: Pds3Table) -> list[dict[str, Any]]:
        """Build a list of column stubs.

        Parameters:
            pds3_table: Object defining the table.

        Returns:
            Dictionaries containing relevant keyword values for each column.
        """
        column_stubs: list[dict[str, Any]] = []
        colnum = 1
        while True:
            try:
                name = pds3_table.old_lookup('NAME', colnum)
            except IndexError:
                break

            column_stubs += [
                {'NAME'          : name,
                 'FORMAT'        : pds3_table.old_lookup('FORMAT', colnum),
                 'ITEMS'         : pds3_table.old_lookup('ITEMS', colnum),
                 'NULL_CONSTANT' : IndexTable._get_null_value(pds3_table, colnum)}]

            colnum += 1

        return column_stubs

    #===========================================================================
    @staticmethod
    def _get_null_value(pds3_table: Pds3Table, colnum: int) -> Any:
        """Determine the null value for a column.

        Parameters:
            pds3_table: Object defining the table.
            colnum: Column number.

        Returns:
            Null value.
        """

        # List of accepted Null keywords
        nullkeys = ['NULL_CONSTANT',
                    'UNKNOWN_CONSTANT',
                    'INVALID_CONSTANT',
                    'MISSING_CONSTANT',
                    'NOT_APPLICABLE_CONSTANT']

        # Check for a known null key in column stub, in priority order.
        nullval = None
        for key in nullkeys:
            if nullval := pds3_table.old_lookup(key, colnum):
                break

        return nullval

    #===========================================================================
    @staticmethod
    def _format_value(value: Any, fmt: str) -> str:
        """Format a single value using a Fortran format code.

        Parameters:
            value: Value to format.
            fmt: FORTRAN-style format code.

        Returns:
            Formatted value.
        """

        # format value
        line = ff.FortranRecordWriter('(' + fmt + ')')
        result = line.write([value])

        # add double quotes to string formats
        if fmt[0] == 'A':
            result = '"' + result.strip().ljust(len(result)) + '"'

        return cast(str, result)

    #===========================================================================
    @staticmethod
    def _format_parms(fmt: str) -> tuple[int, str]:
        """Determine len and type corresponding to a given FORTRAN format code.

        Parameters:
            fmt: FORTRAN-style format code.

        Returns:
            A tuple (width, data_type):
                width: Number of bytes required for a formatted value, including
                       any quotes.
                data_type: Data type corresponding to the format code.
        """

        data_types = {'A': 'CHARACTER',
                      'E': 'ASCII_REAL',
                      'F': 'ASCII_REAL',
                      'I': 'ASCII_INTEGER'}
        try:
            f = IndexTable._format_value('0', fmt)
        except TypeError:
            f = IndexTable._format_value(0, fmt)

        width = len(f)
        data_type = data_types[fmt[0]]

        return (width, data_type)

    #==========================================================================
    @staticmethod
    def _format_column(column_stub: dict[str, Any],
                       value: Any,
                       count: int | None = None) -> str:
        """Format a column.

        Parameters:
            column_stub: Preprocessed column stub.
            value: Value to format.
            count: Number of items to process. If not given, the 'ITEMS' entry is
                used.

        Returns:
            Formatted value.

        Raises:
            ValueError: If count is greater than 1 and the number of supplied
                values does not match count.
        """
        logger = com.get_logger()

        # Get value parameters
        name = column_stub['NAME']
        fmt = column_stub['FORMAT'].strip('"')
        (width, _data_type) = IndexTable._format_parms(fmt)
        if not count:
            count = column_stub['ITEMS'] if column_stub['ITEMS'] else 1

        # Split multiple elements into individual columns and process recursively
        if count > 1:
            if not isinstance(value, (list, tuple)):
                value = count * [value]
            if len(value) != count:
                raise ValueError(
                    'column %s: expected %d values but got %d'
                    % (name, count, len(value)))

            fmt_list = []
            for item in value:
                result = IndexTable._format_column(column_stub, item, count=1)
                fmt_list.append(result)
            return ','.join(fmt_list)

        # Clean up strings
        if isinstance(value, str):
            value = value.strip()
            value = value.replace('\n', ' ')
            while ('  ' in value):
                value = value.replace('  ', ' ')
            value = value.replace('"', '')

        # Format the value
        try:
            result = IndexTable._format_value(value, fmt)
        except TypeError:
            logger.warning("Invalid format: %s %s %s", name, value, fmt)
            result = width * "*"

        if len(result) > width:
            logger.warning("No second format: %s %s %s %s", name, value, fmt, result)

        # Validate the formatted value
        try:
            _ = ast.literal_eval(result)
        except (ValueError, SyntaxError):
            logger.warning('Format error for %s: %s', name, value)

        return result


################################################################################
# Built-in key functions
################################################################################

#===============================================================================
def key__volume_id(label_path: str | Path | FCPath,
                   label_dict: dict[str, Any]) -> str:
    """Key function for VOLUME_ID. The return value will appear in the index
    file under VOLUME_ID.

    Parameters:
        label_path: Path to the PDS label.
        label_dict: Dictionary containing the PDS label fields.

    Returns:
        Volume ID.
    """
    return cast(str, hconf.get_volume_id(label_path))

#===============================================================================
def key__file_specification_name(label_path: str | Path | FCPath,
                                 label_dict: dict[str, Any]) -> FCPath:
    """Key function for FILE_SPECIFICATION_NAME.  The return value will appear in
    the index file under FILE_SPECIFICATION_NAME.

    Parameters:
        label_path: Path to the PDS label.
        label_dict: Dictionary containing the PDS label fields.

    Returns:
        File Specification name.
    """
    label_path = FCPath(label_path)
    return util.get_volume_subdir(label_path, hconf.get_volume_id(label_path))


################################################################################
# external functions
################################################################################

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

################################################################################
