==========================
Cumulative table subsystem
==========================

Overview
========

The cumulative subsystem concatenates the per-volume index and geometry tables
across a whole volume tree into cumulative tables, each with a matching label.
It is implemented in :mod:`metadata_tools.cumulative_support` and produces output
through :func:`~metadata_tools.cumulative_support.create_cumulative_indexes`.

How it works
============

:func:`~metadata_tools.cumulative_support.create_cumulative_indexes` takes the
cumulative output directory (e.g. ``.../GO_0xxx/GO_0999``) and treats its parent
as the volume tree to scan. It parses the command line through
:func:`~metadata_tools.cumulative_support.get_args` and constructs one table
object per table kind, with no output directory:

.. code-block:: python

   tables = [
       geom.SkyTable(level='summary'),
       geom.SkyTable(level='detailed'),
       geom.BodyTable(level='summary'),
       geom.BodyTable(level='detailed'),
       geom.RingTable(level='summary'),
       geom.RingTable(level='detailed'),
       geom.InventoryTable(),
       idx.IndexTable(qualifier='supplemental'),
   ]

Each table object is used only for its ``qualifier`` and ``level``, which name
the per-volume files to gather (for example ``<vol>_body_summary.tab`` or
``<vol>_inventory.csv``). The private ``_cat_rows`` helper walks the tree,
appends the lines of every matching per-volume file, writes the concatenated
file into the cumulative directory (renaming the volume ID to the cumulative
ID), and generates the cumulative label through
:func:`~metadata_tools.label_support.create`.

Invariants
==========

- The cumulative directory and any excluded volumes are skipped during the walk,
  as are ``__skip`` directories.
- The inventory table is written as ``.csv``; all other kinds are ``.tab``.
- A table kind with no per-volume files anywhere in the tree produces no
  cumulative output (it is silently skipped).

API reference
=============

See :doc:`api/cumulative_support`.
