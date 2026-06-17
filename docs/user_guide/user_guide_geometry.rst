=====================
The geometry program
=====================

Each host ships a geometry program named ``<HOST>_geometry.py`` (for Galileo
SSI, ``GO_0xxx_geometry.py``). It reads the supplemental index table for each
volume, computes the geometry backplanes from SPICE through ``oops``, and writes
the geometry tables (and labels) for the bodies, rings, sky, and an inventory of
bodies in each field of view. Under the hood it calls
:func:`~metadata_tools.geometry_support.process.process_tables`.

The index program must have been run first, because the geometry stage reads the
supplemental index file it produced. Run the geometry program from inside the
host directory (see :doc:`user_guide_installation`).

Synopsis
========

.. code-block:: text

   python <HOST>_geometry.py [options] metadata_tree output_tree

Positional arguments
====================

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Argument
     - Description
   * - ``metadata_tree``
     - Path to the top of the tree containing the corrected index files.
   * - ``output_tree``
     - Path to the top of the tree from which to read the supplemental index
       files and in which to write the new geometry tables. This is the tree
       the geometry stage walks.

All path arguments are expanded for environment variables.

Options
=======

Table selection
---------------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Option
     - Description
   * - ``--selection SEL``
     - Which table levels to generate: ``"S"`` for summary tables (one row per
       observation), ``"D"`` for detailed tables (one row per spatial tile), or
       both (``"SD"``). Default: the host's configured selection (``"S"`` for
       the shipped hosts). Case-sensitive.
   * - ``--sampling N``, ``-s``
     - Pixel sampling density used when building the meshgrids. Default: 8.

Volume selection
----------------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Option
     - Description
   * - ``--volumes VOL [VOL ...]``, ``-vv``
     - Process only these volume IDs. Repeatable list. Supplying volumes
       disables ``--new_only``.
   * - ``--exclude VOL [VOL ...]``, ``-e``
     - Volume IDs to skip. Repeatable list. Default: the host's configured
       exclusions (e.g. the cumulative directory ``GO_0999``).
   * - ``--new_only [VOL ...]``, ``-n``
     - Process only volumes that contain no geometry output yet (no
       ``*_inventory.csv``). Useful for resuming an interrupted run.
   * - ``--pattern PATTERN``, ``-p``
     - Glob pattern that further restricts which data files are processed within
       each volume.
   * - ``--first N``, ``-f``
     - Process at most ``N`` input files in each volume. Useful for quick tests.

Output / distribution
---------------------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Option
     - Description
   * - ``--labels``, ``-l``
     - Generate labels only for geometry tables that already exist; do not
       recompute the tables.
   * - ``--task-output FILE``, ``-to``
     - Write a task-queue file listing one task per volume and perform no
       processing. See :doc:`user_guide_cloud`.

Miscellaneous
-------------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Option
     - Description
   * - ``-h``, ``--help``
     - Show the help message and exit.

Example
=======

Generate summary geometry tables for every Galileo SSI volume, then for one
volume, then for a single image matched by pattern:

.. code-block:: bash

   cd src/metadata_tools/hosts/GO_0xxx
   python GO_0xxx_geometry.py "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/"
   python GO_0xxx_geometry.py "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/" \
       -vv GO_0017
   python GO_0xxx_geometry.py "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/" \
       -p "*C0349605600R*"

Results
=======

For each processed volume the program writes, into the volume's output
directory:

- ``<volume>_sky_summary.tab``, ``<volume>_body_summary.tab``, and
  ``<volume>_ring_summary.tab`` (when summary tables are selected);
- the corresponding ``*_detailed.tab`` files (when detailed tables are
  selected);
- ``<volume>_inventory.csv`` listing the bodies in each field of view;
- a matching ``.lbl`` label for each table; and
- a processing log named ``<volume>_geometry-log.txt``.

Observations with no usable pointing (no C-kernel data) are logged and written
with null geometry values.
