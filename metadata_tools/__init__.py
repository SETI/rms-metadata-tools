##########################################################################################
# metadata-tools/__init__.py
##########################################################################################
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

################
Running the code
################

The procedure for generating metadata tables for a given collection is as follows:

 1. Create the supplemental index using <collection>_index.py.
 2. Create the geometry tables using <collection>_geometry.py.
 3. Generate the cumulative tables using <collection>_cumulative.py.

##############################
Generating New Metadata Tables
##############################

 The procedure for creating a new host configuration is as follows:

 1. Create a directory for the new host collection under the hosts/ subdirectory, e.g., 
    hosts/GO_0xxx/, hosts/COISS_xxxx/, etc.
 2. Copy the python files from an existing host directory and rename them as needed
    for the new collection.
 3. Edit the config and init modules as needed.
 4. Create a templates/ subdirectory and copy the files from an existing host. Rename 
    the files as needed.
 5. Edit host_defs.lbl for the new host.
 6. Edit the descriptions in the summary templates as needed.
 7. Edit the supplemental template to define the supplemental metadata for the new host.


#######################
Modifying table columns
#######################

The supplemental index table is controlled by the supplemental label template. By default, 
each column object in the label specifies the name of a PDS label field to add to the table, 
along with its desired formatting. This behavior may be overridden by adding a key function 
to index_config.py of the form:

    key__<NAME>(label_path, label_dict)

where label_path is the path to the PDS label, and label_dict is a dictionary containing the 
PDS label fields. The returned value is placed in the table. 

Modifying the geometry tables requires editing of the column definition and format tables,
and may require the addition of new backplane functions.

To add a new geometry column:
   1. Add a column definition to column definition file, e.g. COLUMNS_BODY.py.
   2. Add a corresponding function to appropriate backplane module.
   3. Add a row to the format dictionary in geometry_support.py.
   4. Add column description(s) to the label template, e.g., body_summary.lbl.

"""
##########################################################################################
__all__ = ['get_common_args']

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


##########################################################################################
# Logger management
##########################################################################################

# Define the global logger with streamlined output, no handlers so printing to stdout
_LOGGER = PdsLogger.get_logger('metadata', timestamps=False, digits=0, lognames=False,
                               pid=False, indent=True, blanklines=False, level='info')

SYSTEM_NULL = "NONE"

#=========================================================================================
def get_logger():
    """The global PdsLogger for the metadata tools."""
    return _LOGGER

##########################################################################################
# Argument parser
##########################################################################################

#=========================================================================================
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

##########################################################################################
# Table class
##########################################################################################
class Table(object):
    """Class describing a single table for a single volume.
    """

    #=====================================================================================
    def __init__(self, output_dir=None,
                 volume_id=None, level=None, qualifier=None, prefix=None,
                 suffix=None, use_global_template=False):
        """Constructor for a table object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the index files.
            volume_id (str): Volume ID.
            level (str, optional):
                Processing level: "summary", "detailed", or "index".
            qualifier (str):
                "sky", "sun", "ring", "body", "inventory", or "supplemental".
            prefix (str): File path prefix.
            suffix (str): File name suffix.
            use_global_template (bool):
                If True, the label template is to be found in the global
                template directory.

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

    #=====================================================================================
    def write(self, labels_only=False):
        """Write a table and its label.

        Args:
            labels_only (bool, optional):
                If True, labels are generated for any existing geometry
                tables.

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

##########################################################################################
