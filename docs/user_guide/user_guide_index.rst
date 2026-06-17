==========================
The index program
==========================

Each host ships an index program named ``<HOST>_index.py`` (for Galileo SSI,
``GO_0xxx_index.py``). It generates the supplemental index table and its PDS3
label for every volume in a tree, by reading each data product's PDS3 label.
Under the hood it calls :func:`~metadata_tools.index_support.process_index`.

Run it from inside the host directory (see :doc:`user_guide_installation`).

Synopsis
========

.. code-block:: text

   python <HOST>_index.py [options] volume_tree metadata_tree output_tree

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
   * - ``--volumes VOL [VOL ...]``, ``-vv``
     - Process only these volume IDs (e.g. ``GO_0017``). Repeatable list. If
       omitted, every volume in the tree is processed.
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

Processing / distribution
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Option
     - Description
   * - ``--task-output FILE``, ``-to``
     - Write a task-queue file listing one task per volume and perform no
       processing. Used to drive the distributed cloud workers; see
       :doc:`user_guide_cloud`.

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

   cd src/metadata_tools/hosts/GO_0xxx
   python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/"
   python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" -vv GO_0017

Results
=======

For each processed volume ``<volume>``, the program writes
``<volume>_supplemental_index.tab`` and ``<volume>_supplemental_index.lbl`` into
the corresponding volume directory of the output tree, and a processing log
named ``<volume>_index-log.txt``. Columns that never received a non-null value
across the run are reported as a warning at the end of the log.
