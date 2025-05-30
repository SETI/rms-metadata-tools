################################################################################
# metadata-tools/__init__.py
################################################################################
"""PDS Ring-Moon Systems Node, SETI Institute

``metadata-tools`` is a Python module that generates index and geometry
metadata tables and their corresponding PDS3 labels. Each line of the table
contains metadata for a single data file (e.g. image).

Index files contain descriptive information about the data product, like
observation times, exposures, instrument modes and settings, etc. Index file
entries are taken from the label for the data product by default, but may
instead be derived from label quantities by defining the appropriate
configuration function in the host_config.py for the specific host.

Raw index files are provided by each project, with varying levels of
compliance. The project-supplied index files are modified to produce the
corrected index  files that can be used with the host from_index() method.
The ``metadata-tools`` package is intended to produce supplemental index
files, which add columns to the corrected index file. Supplemental index
files are identical in structure to index files, so this package can
generate any kind of index file. Supplemental index files can be provded as
arguments to from_index() to create a merged dictionary.

Supplemental index files are used as input to OPUS, and are available via
viewmaster to be downloaded by PDS users.

Geometry files tabulate the values of geometrc quantites for each data file,
which are derived from SPICE using the information in the index file or from
the PDS3 label using OOPS.  The purpose of the geometry files is to provide
input to OPUS.

##############################
Generating New Matadata Tables
##############################

The procedure for generating metadata tables is as follows:

 1. Create a directory for the new host collection under the hosts/
    subdirectory, e.g., GO_0xxx, COISS_xxxx, etc.

 2. Copy the python files from an existing host directory and rename them
    according to the new collection.  You should have six files:

    __init.py__
    host_init.py
    host_config.py
    <collection>_index.py
    <collection>_geometry.py
    <collection>_cumulative.py

 3. Create a templates/ subdirectory and copy the label templates from an
    exsting host, and rename accordingly, yielding:

    templates/<collection>_supplmental_index.lbl
    templates/<collection>_body_summary.lbl
    templates/<collection>_ring_summary.lbl
    templates/host_defs.lbl
    templates/host_description.lbl

 4. Edit the supplemental and summary templates and generate the tables
    using <collection>_index.py and <collection>_geometry.py according to
    the instructions in those files.

 5. Generate the cumulative tables using <collection>_cumulative.py
    according to the instructions in that file.

##########
Unit Tests
##########

Copy and edit the unit tests from the tests/ directory of an existing host.
Run all tests from the rms-metadata-tools/ directory using:

    python -m unitest

"""
################################################################################
import re
import argparse

from filecache import FCPath
from pdslogger import PdsLogger

import metadata_tools.util as util
import metadata_tools.label_support as lab

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    __version__ = 'Version unspecified'


################################################################################
# Logger management
################################################################################

# Define the global logger with streamlined output, no handlers so printing to stdout
_LOGGER = PdsLogger.get_logger('metadata', timestamps=False, digits=0, lognames=False,
                               pid=False, indent=True, blanklines=False, level='info')

SYSTEM_NULL = "NONE"

#===============================================================================
def get_logger():
    """The global PdsLogger for the metadata tools."""
    return _LOGGER

################################################################################
# Argument parser
################################################################################

#===============================================================================
def get_common_args(host=None):
    """Common argument parser for metadata tools.

        Args:
            host (str): Host name e.g. 'GO_0xxx'.

         Returns:
            argparser.ArgumentParser :
                Parser containing the common argument specifications.
   """
    # Action method for path arguments
    class PathAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            vals = re.sub('://', '<<token>>', values)
            vals = re.sub('//*', '/', vals)
            vals = re.sub('<<token>>', '://', vals)
            setattr(namespace, self.dest, vals)

    # Define parser
    parser = argparse.ArgumentParser(
                    description='Metadata generation utility%s.'
                                % ('' if not host else
                                   ' for ' + host))

    # Generate parser
    gr = parser.add_argument_group('Common Arguments')
    gr.add_argument('input_tree', type=str, metavar='input_tree',
                    help='''File path to the top to tree containing the
                            volume files.''', action=PathAction)
    gr.add_argument('output_tree', type=str, metavar='output_tree',
                    help='''File path to the top to tree in which to place the
                            volume files.''')
    gr.add_argument('volumes', type=str, nargs='*', metavar='volumes',
                    help='''If given, only these volumes are processed.''')
    gr.add_argument('--labels', '-l', nargs='*', type=str, metavar='labels',
                    default=False,
                    help='''If given, labels are generated for existing files.''')

    # Return parser
    return parser

################################################################################
# Table class
################################################################################
class Table(object):
    """Class describing a single table for a single volume.
    """

    #===========================================================================
    def __init__(self, output_dir=None,
                 volume_id=None, level=None, qualifier=None, prefix=None,
                 suffix=None, use_global_template=False):
        """Constructor for a table object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the index files.
            volume_id (str): Volume ID.
            level (str, optional): Processing level: "summary", "detailed", or "index".
            qualifier (str): "sky", "sun", "ring", "body", "inventory", or "supplemental".
            prefix (str): File path prefix.
            suffix (str): File name suffix.
            use_global_template (bool):
                If True, the label template is to be found in the global template
                directory.

        """
        self.volume_id = volume_id
        self.level = level
        self.qualifier = qualifier
        self.use_global_template = use_global_template

        if not output_dir:
            return

        if not suffix:
            suffix = "_%s_%s.tab" % (self.qualifier, self.level)
        prefix = output_dir.joinpath(self.volume_id).as_posix()
        self.filename = FCPath(prefix + suffix)

        self.rows = []

    #===========================================================================
    def write(self, labels_only=False):
        """Write a table and its label.

        Args:
            labels_only (bool, optional):
                If True, labels are generated for any existing geometry tables.

        Returns:
            None.
        """
        logger = get_logger()

        if not labels_only:
            if self.rows == []:
                return

            # Write table
            logger.info("Writing:", self.filename)
            util.write_txt_file(self.filename, self.rows)

        # Write label
        table_type = self.qualifier
        if self.level:
            table_type += '_' + self.level
        lab.create(self.filename,
                   table_type=table_type, use_global_template=self.use_global_template)

################################################################################
