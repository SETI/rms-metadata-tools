################################################################################
# index_support.py - Tools for generating index files
################################################################################
import fortranformat as ff
import fnmatch
import warnings
import hosts.pds3 as pds3

import metadata_tools as meta
import metadata_tools.util as util
import pdstable

from pdsparser             import Pds3Label
from filecache             import FCPath
from pdstemplate.pds3table import Pds3Table

import host_config as config

################################################################################
# IndexTable class
################################################################################
class IndexTable(meta.Table):
    """Class describing an index table for a single volume.
    """

    #===========================================================================
    def __init__(self, input_dir=None, output_dir=None, qualifier='', glob=None,
                 **kwargs):
        """Constructor for an IndexTable object.

        Args:
            input_dir (str, Path, or FCPath):
                Directory containing the volume, specifically the data labels.
            output_dir (str, Path, or FCPath):
                Directory in which to find the "updated" index file (e.g.,
                <volume>_index.tab, and in which to write the new index files.
            qualifier (str, optional):
                Qualifying string identifying the type of index file to create,
                e.g., 'supplemental'.
            glob (str, optional): Glob pattern for index files.
        """

        # Initialize table, return if specific paths not given
        super().__init__(output_dir, level="index", qualifier=qualifier, **kwargs)
        if not input_dir:
            return

        # Save inputs
        self.input_dir = FCPath(input_dir)
        self.output_dir = FCPath(output_dir)
        self.glob = glob
        self.usage = {}
        self.unused = set()

        # Get volume id
        self.volume_id = config.get_volume_id(self.input_dir)

        logger = meta.get_logger()
        s = ' '+qualifier if qualifier else ' primary'
        logger.info('New%s index for %s.' % (s, self.volume_id))

        # Get relevant filenames and paths
        primary_index_name = util.get_index_name(self.input_dir, self.volume_id, None)
        index_name = util.get_index_name(self.input_dir, self.volume_id, qualifier)
        template_name = util.get_template_name(index_name, self.volume_id)
        self.index_path = self.output_dir/(index_name + '.tab')

        # If the index name is the same as the primary inxex name,
        # then this is the primary index.
        create_primary = index_name == primary_index_name

        # If there is a primary file, read it and build the file list
        if not create_primary:
            self.primary_index_label_path = self.output_dir/(primary_index_name + '.lbl')
            self.primary_index_path = self.output_dir/(primary_index_name + '.tab')

            try:
                local_label_path = self.primary_index_label_path.retrieve()
                table = pdstable.PdsTable(local_label_path)
            except FileNotFoundError:
                warnings.warn('Primary index file not found: %s. '
                              'Skipping' % self.primary_index_label_path)
                return

            primary_row_dicts = table.dicts_by_row()
            self.files = [FCPath(primary_row_dict['FILE_SPECIFICATION_NAME'])
                          for primary_row_dict in primary_row_dicts]

            for i in range(len(self.files)):
                self.files[i] = self.input_dir/self.files[i].with_suffix('.LBL')

        # Otherwise, build the file list from the directory tree
        else:
            self.files = [f for f in input_dir.rglob('*.LBL')]

        # Extract relevent fields from the template
        template_path = FCPath('./templates/')/(template_name + '.lbl')
        label_name = util.get_index_name(self.input_dir, self.volume_id, qualifier)
        label_path = self.output_dir / FCPath(label_name + '.lbl')

        template = util.read_txt_file(template_path, as_string=True)
        pds3_table = Pds3Table(label_path, template, validate=False,
                               numbers=True, formats=True)
        self.column_stubs = IndexTable._get_column_values(pds3_table)

    #===========================================================================
    def create(self, labels_only=False):
        """Create the index file for a single volume.

        Args:
            labels_only (bool):
                If True, labels are generated for any existing geometry tables.

        Returns:
            None.
        """
        if not hasattr(self, 'files'):
            return

        logger = meta.get_logger()

        # Open the output file; create dir if necessary
        try:
            self.output_dir.mkdir(exist_ok=True)
        except NotImplementedError:
            pass        ### need to check for existence.

        # Build the index
        n = len(self.files)
        if not labels_only:
            for i in range(n):
                file = self.files[i]
                name = file.name
                root = file.parent

                # Match the glob pattern
                file = fnmatch.filter([name], self.glob)[0]
                if file == []:
                    continue

                # Log volume ID and subpath
                subdir = util.get_volume_subdir(root, config.get_volume_id(root))
                logger.info('%s %4d/%4d  %s' % (self.volume_id, i+1, n, subdir/name))

                # Make the index for this file
                self.add(root, file)

            # Flag any unused columns
            for name in self.usage:
                if not self.usage[name]:
                    self.unused.update({name})

        # Write tables and make labels
        self.write(labels_only=labels_only)

    #===========================================================================
    def add(self, root, name):
        """Write a single index file entry.

        Args:
            root (str): Top of the directory tree containing the volume.
            name (str): Name of PDS label.

        Returns:
            None.
        """

        # Read the PDS3 label
        path = root/name
        label = pds3.get_label(path.as_posix())
#        label = Pds3Label(path, method='fast')

        # Write columns
        first = True
        line = ''
        for column_stub in self.column_stubs:
            if not column_stub:
                continue

            # Add column name to usage dict if not already there
            name = column_stub['NAME']
            if name not in self.usage:
                self.usage[name] = False

            # Get the value
            value = self._index_one_value(column_stub, path, label)

            # Write the value into the index
            if not first:
                line += ","

            fvalue = IndexTable._format_column(column_stub, value)
            line += fvalue

            first = False

        self.rows += [line]

    #===========================================================================
    def _index_one_value(self, column_stub, label_path, label_dict):
        """Determine value for one row of one column.

        Args:
            column_stub (dict): Column stub dictionary.
            label_path (str, Path, or FCPath): Path to the PDS label.
            label_dict (dict): Dictionary containing the PDS label fields.

        Returns:
            str: Determined value.
        """
        nullval = column_stub['NULL_CONSTANT']

        # Check for built-in key function
        key = column_stub['NAME']
        fn_name = 'key__' + key.lower()
        try:
            fn = globals()[fn_name]
            value = fn(label_path, label_dict)

        # Check for key function in index_config module
        except KeyError:
            try:
                fn = getattr(config, fn_name)
                value = fn(label_path, label_dict)

            # If no key function, just take the value from the label
            except AttributeError:
                value = label_dict[key] if key in label_dict else nullval

        # If a key function returned None, insert a NULL value.
        if value is None:
            value = nullval

        assert value is not None, 'Null constant needed for %s.' % column_stub['NAME']

        # If valid value, mark this column as used
        if value != nullval:
            self.usage[key] = True

        return value

    #===========================================================================
    @staticmethod
    def _get_column_values(pds3_table):
        """Build a list of column stubs.

        Args:
            pds3_table (Pds3Tabel): Object defining the table.

        Returns:
            list: Dictionaries containing relevant keyword values for each column.
        """
        column_stubs = []
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
    def _get_null_value(pds3_table, colnum):
        """Determine the null value for a column.

        Args:
            pds3_table (Pds3Tabel): Object defining the table.
            column (int): Column number.

        Returns:
            str|float: Null value.
        """

        # List of accepted Null keywords
        nullkeys = ['NULL_CONSTANT',
                    'UNKNOWN_CONSTANT',
                    'INVALID_CONSTANT',
                    'MISSING_CONSTANT',
                    'NOT_APPLICABLE_CONSTANT']

        # Check for a known null key in column stub
        nullval = None
        for key in nullkeys:
            if nullval := pds3_table.old_lookup(key, colnum):
                continue

        return nullval

    #===========================================================================
    @staticmethod
    def _format_value(value, format):
        """Format a single value using a Fortran format code.

        Args:
            value (str): Value to format.
            format (str): FORTRAN-style format code.

        Returns:
            str: formatted value.
        """

        # format value
        line = ff.FortranRecordWriter('(' + format + ')')
        result = line.write([value])

        # add double quotes to string formats
        if format[0] == 'A':
            result = '"' + result.strip().ljust(len(result)) + '"'

        return result

    #===========================================================================
    @staticmethod
    def _format_parms(format):
        """Determine len and type corresopnding to a given FORTRAN format code..

        Args:
            format (str): FORTRAN_style format code.

        Returns:
            NamedTuple (width (int), data_type (str)):
                width     (int): Number of bytes required for a formatted value,
                          including any quotes.
                data_type (str): Data type corresponding to the format code.
        """

        data_types = {'A': 'CHARACTER',
                      'E': 'ASCII_REAL',
                      'F': 'ASCII_REAL',
                      'I': 'ASCII_INTEGER'}
        try:
            f = IndexTable._format_value('0', format)
        except TypeError:
            f = IndexTable._format_value(0, format)

        width = len(f)
        data_type = data_types[format[0]]

        return (width, data_type)

    #===============================================================================
    @staticmethod
    def _format_column(column_stub, value, count=None):
        """Format a column.

        Args:
            column_stub (list): Preprocessed column stub.
            value (str): Value to format.
            count (int): Number of items to process.  If not given, the 'ITEMS'
                         entry is used.

        Returns:
            str: Formatted value.
        """
        logger = meta.get_logger()

        # Get value parameters
        name = column_stub['NAME']
        format = column_stub['FORMAT'].strip('"')
        (width, data_type) = IndexTable._format_parms(format)
        if not count:
            count = column_stub['ITEMS'] if column_stub['ITEMS'] else 1

        # Split multiple elements into individual columns and process recursively
        if count > 1:
            if not isinstance(value, (list, tuple)):
                value = count * [value]
            assert len(value) == count

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
            result = IndexTable._format_value(value, format)
        except TypeError:
            logger.warn("Invalid format: %s %s %s" % (name, value, format))
            result = width * "*"

        if len(result) > width:
            logger.warn("No second format: %s %s %s %s" % (name, value, format, result))

        # Validate the formatted value
        try:
            test = eval(result)
        except Exception:
            logger.warn('Format error for %s: %s' % (name, value))

        return result


################################################################################
# Built-in key functions
################################################################################

#===============================================================================
def key__volume_id(label_path, label_dict):
    """Key function for VOLUME_ID. The return value will appear in the index
    file under VOLUME_ID.

    Args:
        label_path (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: Volume ID
    """
    return config.get_volume_id(label_path)

#===============================================================================
def key__file_specification_name(label_path, label_dict):
    """Key function for FILE_SPECIFICATION_NAME.  The return value will appear in
    the index file under FILE_SPECIFICATION_NAME.

    Args:
        label_path (str, Path, or FCPath): Path to the PDS label.
        label_dict (dict): Dictionary containing the PDS label fields.

    Returns:
        str: File Specification name.
    """
    return util.get_volume_subdir(label_path, config.get_volume_id(label_path))


################################################################################
# external functions
################################################################################

#===============================================================================
def get_args(host=None, index_type=None):
    """Argument parser for index files.

    Args:
        host (str): Host name e.g. 'GOISS'.
        index_type (str, optional):
            Qualifying string identifying the type of index file
            to create, e.g., 'supplemental'.

     Returns:
        argparser.ArgumentParser :
            Parser containing the argument specifications.
   """

    # Get parser with common args
    parser = meta.get_common_args(host=host)

    # Add parser for index args
    gr = parser.add_argument_group('Index Arguments')
    gr.add_argument('--type', '-t', type=str, metavar='type',
                    default=index_type,
                    help='''Type of index file to create, e.g.,
                            "supplemental".''')

    # Return parser
    return parser

#===============================================================================
def process_index(template_name, glob=None):
    """Creates index files for a collection of volumes.

    Args:
        template_name (str): Name of input template.
        glob (str, optional): Glob pattern for index files.

    Returns:
        None.
    """
    logger = meta.get_logger()

    # Parse arguments
    host, index_type = util.parse_template_name(template_name)
    parser = get_args(host=host, index_type=index_type)
    args = parser.parse_args()

    input_tree = FCPath(args.input_tree)
    output_tree = FCPath(args.output_tree)
    volumes = args.volumes
    labels_only = args.labels is not False

    # Build volume glob
    vol_glob = util.get_volume_glob(input_tree.name)

    # Walk the input tree, making indexes for each found volume
    for root, dirs, files in input_tree.walk():
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

        unused = None
        # Test whether this root is a volume
        if fnmatch.filter([vol], vol_glob):
            if not volumes or vol in volumes:
                indir = root
                if output_tree.parts[-1] != col:
                    outdir = output_tree/col
                outdir = output_tree/vol

                # Process this volumne
                index = IndexTable(indir, outdir,
                                   qualifier=args.type, volume_id=vol, glob=glob)
                index.create(labels_only=labels_only)

                unused = index.unused if not unused else unused & index.unused

        # Log a warning for any columns that never had non-null values
        if unused:
            logger.warn('Unused columns: %s', unused)

################################################################################