=======================
The cumulative program
=======================

The ``metadata-cumulative`` console script walks the volume tree and
concatenates the per-volume index and geometry tables into cumulative tables
that span the whole collection, writing a matching label for each. Under the
hood it calls
:func:`~metadata_tools.cumulative_support.create_cumulative_indexes`.

Run it after the index and geometry programs.

Synopsis
========

.. code-block:: text

   metadata-cumulative HOST_ID [options] output_dir

Positional arguments
====================

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Argument
     - Description
   * - ``output_dir``
     - Directory in which to write the cumulative files. This is a dedicated
       cumulative volume directory (e.g. ``.../GO_0xxx/GO_0999/``); its parent
       is taken as the volume tree to concatenate.

The path argument is expanded for environment variables.

Options
=======

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Option
     - Description
   * - ``--exclude VOL [VOL ...]``, ``-e``
     - Volume IDs to skip while concatenating. Repeatable list. Default: the
       host's configured exclusions (the cumulative directory itself, e.g.
       ``GO_0999``).
   * - ``--volumes VOL [VOL ...]``
     - Concatenate only these volume IDs.
   * - ``--labels``, ``-l``
     - Generate the cumulative labels only, from existing cumulative tables.
   * - ``--pattern PATTERN``, ``-p``
     - Glob pattern used to select files.
   * - ``-h``, ``--help``
     - Show the help message and exit.

Example
=======

Build the cumulative tables for Galileo SSI, then for one volume only:

.. code-block:: bash

   metadata-cumulative GO_0xxx "$RMS_METADATA_TEST/GO_0xxx/GO_0999/"
   metadata-cumulative GO_0xxx "$RMS_METADATA_TEST/GO_0xxx/GO_0999/" --volumes GO_0017

Results
=======

The program writes one cumulative table per table kind into ``output_dir``,
named with the cumulative directory's volume ID (e.g.
``GO_0999_supplemental_index.tab``, ``GO_0999_body_summary.tab``,
``GO_0999_inventory.csv``), each with a matching ``.lbl`` label. Table kinds for
which no per-volume tables are found are skipped.
