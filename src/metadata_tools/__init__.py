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
corrected index files that can be used with the host from_index() method.
The ``metadata-tools`` package is intended to produce supplemental index
files, which add columns to the corrected index file. Supplemental index
files are identical in structure to index files, so this package can
generate any kind of index file. Supplemental index files can be provided as
arguments to from_index() to create a merged dictionary.

Supplemental index files are used as input to OPUS, and are available via
viewmaster to be downloaded by PDS users.

Geometry files tabulate the values of geometric quantities for each data file,
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
   1. Add a column definition to a column definition file, e.g. columns/body.py.
   2. Add a corresponding function to appropriate backplane module.
   3. Add a row to the format dictionary in geometry_support.py.
   4. Add column description(s) to the label template, e.g., body_summary.lbl.

"""
##########################################################################################
try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    __version__ = 'Version unspecified'
