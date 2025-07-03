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

##############################
Generating New Matadata Tables
##############################

The procedure for generating metadata tables is as follows:

 1. Create a directory for the new host collection under the hosts/
    subdirectory, e.g., GO_0xxx, COISS_xxxx, etc.

 2. Copy the python files from an existing host directory and rename them
    according to the new collection.  You should have these files:

    __init.py__
    host_init.py
    host_config.py
    index_config.py
    geometry_config.py
    <collection>_index.py
    <collection>_geometry.py
    <collection>_cumulative.py

 3. Create a templates/ subdirectory and copy the label templates from an
    existing host, and rename accordingly, yielding:

    templates/<collection>_supplmental_index.lbl
    templates/<collection>_body_summary.lbl
    templates/<collection>_ring_summary.lbl
    templates/host_defs.lbl

 4. Edit the config modules as needed.

 5. Edit the supplemental and summary templates and generate the tables
    using <collection>_index.py and <collection>_geometry.py according to
    the instructions in those files.

 6. Generate the cumulative tables using <collection>_cumulative.py
    according to the instructions in that file.

"""
##########################################################################################
#from metadata_tools.index_support import process_index
#from metadata_tools.geometry_support import process_tables
#from metadata_tools.cumulative_support import create_cumulative_indexes
#__all__ = ['process_index', 'process_tables', 'create_cumulative_indexes']

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    __version__ = 'Version unspecified'
