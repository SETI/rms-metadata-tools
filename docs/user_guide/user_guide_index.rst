==========================
The index program
==========================

The ``metadata-index`` console script generates the supplemental index table
and its PDS3 label for every volume in a tree, by reading each data product's
PDS3 label. Under the hood it calls
:func:`~metadata_tools.index_support.process_index`.

Synopsis
========

.. code-block:: text

   metadata-index HOST_ID [options] volume_tree metadata_tree output_tree

Positional arguments
====================

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Argument
     - Description
   * - ``volume_tree``
     - Path to the top of the tree containing the volume data files,
       specifically the PDS3 labels that are read for each row.
   * - ``metadata_tree``
     - Path to the top of the tree containing the metadata files, specifically
       the project-supplied corrected index files (``<volume>_index.tab``).
   * - ``output_tree``
     - Path to the top of the tree in which to write the new supplemental index
       files and labels.

All path arguments are expanded for environment variables.

Options
=======

Selection
---------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Option
     - Description
   * - ``--volumes VOL [VOL ...]``
     - Process only these volume IDs (e.g. ``GO_0017``). If omitted, every
       volume in the tree is processed.
   * - ``--pattern PATTERN``, ``-p``
     - Glob pattern that further restricts which data files are processed
       within each volume.

Output / type
-------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Option
     - Description
   * - ``--type TYPE``, ``-t``
     - Type of index file to create, e.g. ``supplemental``. Default: taken from
       the host's template name (``supplemental`` for the shipped hosts).
   * - ``--labels``, ``-l``
     - Generate labels only for index tables that already exist; do not
       recompute the tables themselves.

Miscellaneous
-------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Option
     - Description
   * - ``-h``, ``--help``
     - Show the help message and exit.

Example
=======

Generate supplemental index tables for every Galileo SSI volume, then for one
volume only:

.. code-block:: bash

   metadata-index GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/"
   metadata-index GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --volumes GO_0017

Results
=======

For each processed volume ``<volume>``, the program writes
``<volume>_supplemental_index.tab`` and ``<volume>_supplemental_index.lbl`` into
the corresponding volume directory of the output tree, and a processing log
named ``<volume>_index-log.txt``. Columns that never received a non-null value
across the run are reported as a warning at the end of the log.
