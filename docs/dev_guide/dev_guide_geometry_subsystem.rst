========================
Geometry table subsystem
========================

Overview
========

The geometry subsystem computes geometric quantities for each observation and
writes them as tables. It is the ``geometry_support`` package; the
:doc:`dev_guide_architecture` chapter introduces its principal classes. This
chapter describes the modules and the contracts that are easy to get wrong.

Entry point
===========

:func:`~metadata_tools.geometry_support.process.process_tables` (in
:mod:`metadata_tools.geometry_support.process`) parses the command line through
:func:`~metadata_tools.geometry_support.process.get_args` and walks the **output** tree
(the tree that already holds the supplemental index files). For each volume it
constructs a :class:`~metadata_tools.geometry_support.suite.Suite` and calls
:meth:`~metadata_tools.geometry_support.suite.Suite.create`. The ``--new_only``
option skips volumes that already contain an ``*_inventory.csv``; supplying
explicit volumes disables it.

Suite
=====

:class:`~metadata_tools.geometry_support.suite.Suite` reads the volume's
observations through the host's ``from_index`` hook, builds the per-mode
meshgrids once, and creates a list of tables for each requested level (an
inventory table plus sky, ring, and body tables). It loops over observations,
building a :class:`~metadata_tools.geometry_support.record.Record` per level and
dispatching each record to every table whose level matches. A ``RuntimeError`` is
raised if a volume contains more than one index file.

Record and prep
===============

:class:`~metadata_tools.geometry_support.record.Record` holds one observation's
state: the primary body (from
:func:`~metadata_tools.geometry_support.bodies_select.get_primary`), the selected
bodies, the ``oops`` backplane, and the level-specific column dictionaries from
the :mod:`metadata_tools.columns` package.
:meth:`~metadata_tools.geometry_support.record.Record.add` calls
:func:`~metadata_tools.geometry_support.prep.prep_row`, which evaluates each
column's backplane key, applies the excluded-pixel mask, and formats the result;
:meth:`~metadata_tools.geometry_support.record.Record.postprocess` then applies
the null-linking rules so that linked columns go null together.

Masks
=====

:func:`~metadata_tools.geometry_support.masks.construct_excluded_mask` builds the
boolean mask of pixels to exclude for a column, honoring the column's masker,
shadower, and face codes. It depends only on ``oops`` and ``numpy`` so it can be
unit-tested without a host plugin.

Formatting and formats
======================

:func:`~metadata_tools.geometry_support.formatting.formatted_column` turns a
masked ``oops`` scalar into one or two formatted column strings, converting
radians to degrees, handling cyclic (longitude) ranges, ISO times, null values,
valid-range clipping, and overflow. It is driven by an entry from
:data:`~metadata_tools.geometry_support.formats.FORMAT_DICT`.

.. _format-dict-contract:

The format-dictionary contract
==============================

:data:`~metadata_tools.geometry_support.formats.FORMAT_DICT` maps each column
name to a ten-element tuple:

.. code-block:: text

   (flag, number_of_values, column_width, standard_format, overflow_format,
    null_value, valid_minimum, valid_maximum, link_id, link)

where ``flag`` controls unit conversion (``"RAD"``/``"DEG"`` radians to degrees,
``"360"`` degrees with 360-degree periodicity, ``"-180"`` the
``(-180, 180)`` range, ``"ISO"`` time, ``""`` no change), and ``link_id`` /
``link`` tie columns together for null-linking.
:data:`~metadata_tools.geometry_support.formats.ALT_FORMAT_DICT` holds alternate
formats keyed by ``(column_name, alt_format_tag)``.

Body selection
==============

:mod:`metadata_tools.geometry_support.bodies_select` decides which bodies appear
in a record: the primary and secondaries are always included; children of the
primary and any additions are included when they intersect the field of view;
the target and its parent are always included. It also produces the
field-of-view inventory and, when SPICE pointing is unavailable, sets the
record's ``pointing_available`` flag so the row is written with null geometry.

Important invariants
====================

- **Units.** Backplane values are in radians; columns whose ``flag`` is
  ``"RAD"``, ``"DEG"``, ``"360"``, or ``"-180"`` are converted to degrees by
  :func:`~metadata_tools.geometry_support.formatting.formatted_column`. Do not
  pre-convert.
- **Column-description tuples.** A column description is
  ``(backplane_key, (masker, shadower, face))`` with an optional trailing
  alternate-format tag. The masker/shadower strings concatenate ``"P"`` (planet),
  ``"R"`` (rings), and ``"M"`` (blocker body); the face is ``"D"``, ``"N"``, or
  ``""``. These tuples live in the :mod:`metadata_tools.columns` package.
- **Meshgrids** are built once per :class:`~metadata_tools.geometry_support.suite.Suite`
  and selected per observation by telemetry mode; they are not rebuilt per row.
- **Summary vs. detailed.** A summary call writes exactly one row per
  observation, even if every value is null; a detailed call writes only rows for
  non-empty tiles.

API reference
=============

See :doc:`api/geometry_support` and :doc:`api/columns`.
