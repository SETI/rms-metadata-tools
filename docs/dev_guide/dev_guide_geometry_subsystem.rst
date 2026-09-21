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
meshgrids once, and builds the table list: one level-independent inventory
table plus sky, ring, and body tables for each requested level. It loops over
observations, building a :class:`~metadata_tools.geometry_support.record.Record`
per level and dispatching each record to every table whose level matches; the
inventory table receives one record per observation. A ``RuntimeError`` is
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

where ``flag`` controls unit conversion (``"DEG"`` radians to degrees,
``"360"`` degrees with 360-degree periodicity, ``"-180"`` the
``(-180, 180)`` range, ``"ISO"`` time, ``"KM"`` kilometers, ``""`` no change),
and ``link_id`` /
``link`` tie columns together for null-linking.
:data:`~metadata_tools.geometry_support.formats.ALT_FORMAT_DICT` holds alternate
formats keyed by ``(column_name, alt_format_tag)``.

Body selection
==============

The candidates come from the host's **mission table**
(``MISSION_TABLE`` in ``geometry_config.py``): one row per mission phase, giving
an SCLK range, exception patterns for observations to skip, and that phase's
primary, secondaries, selections, and additions.
:func:`~metadata_tools.geometry_support.formats.get_mission_table` converts the
SCLK strings to ticks once per host and caches the result (the conversion needs
SPICE), and :func:`~metadata_tools.geometry_support.bodies_select.get_primary`
picks the row whose SCLK range contains the observation's clock count — an
observation matching a row's exceptions gets no primary and is written with
null geometry.

:mod:`metadata_tools.geometry_support.bodies_select` then decides which bodies
appear in the record: the primary and secondaries are always included; children
of the primary are included when they intersect the field of view (restricted
to the selections when the row lists any); with no primary, the selections that
intersect the field of view are used instead; additions are included whenever
they intersect the field of view; and the target and, for a satellite, its
parent are always included. It also produces the field-of-view inventory and,
when SPICE pointing is unavailable, sets the record's ``pointing_available``
flag so the row is written with null geometry.

Important invariants
====================

- **Units.** Backplane values are in radians; columns whose ``flag`` is
  ``"DEG"``, ``"360"``, or ``"-180"`` are converted to degrees by
  :func:`~metadata_tools.geometry_support.formatting.formatted_column`. Do not
  pre-convert.
- **Column-description tuples.** A column description is
  ``(backplane_key, (masker, shadower, face))`` with an optional trailing
  alternate-format tag. The masker/shadower strings concatenate ``"P"`` (planet),
  ``"R"`` (rings), and ``"M"`` (blocker body); the face is ``"D"``, ``"N"``, or
  ``""``. These tuples live in the :mod:`metadata_tools.columns` package.
- **Meshgrids** are built once per :class:`~metadata_tools.geometry_support.suite.Suite`
  and selected per observation by telemetry mode; they are not rebuilt per row.
- **One row per observation.** A call produces at most one row; with the
  default ``allow_zero_rows=True`` an all-null row is dropped (pass
  ``allow_zero_rows=False`` to force it).

Removed capability: detailed (tiled) tables
===========================================

The subsystem once carried a second processing level, *detailed*, removed
because it had never been wired up. This section records what it was, so that
the design is not lost if it is ever wanted again.

**What it was.** Alongside each ``<vol>_<kind>_summary.tab`` a detailed run
would emit ``<vol>_<kind>_detailed.tab`` holding one row per non-empty spatial
subregion ("tile") per observation, rather than one row per observation. An
extra tile-index column was inserted after the body-name prefix columns. The
level was chosen with ``--selection``, which accepted ``"S"``, ``"D"``, or
``"SD"``; ``Suite`` built one table set per selected level and one ``Record``
per level, and dispatched each record to the tables whose level matched.

**Column sets.** Every detailed list was a strict prefix of the corresponding
summary list — the per-pixel columns without the gridless ones, since a
whole-body quantity like the sub-solar longitude does not vary across tiles.
``BODY_DETAILED_COLUMNS`` was ``BODY_COLUMNS``; ``RING_DETAILED_COLUMNS`` was
``RING_COLUMNS + ANSA_COLUMNS``; ``SUN_DETAILED_COLUMNS`` was ``SUN_COLUMNS``;
sky shared a single list.

**Tiling definitions.** Bodies were tiled into latitude bands every 20° between
±70°, with a ``where_in_front`` / ``where_sunward`` overlay. Rings were tiled
into azimuth bands spanning 0.20π–1.80π, split into inner and outer sets at a
ring radius of 150,000 km. Sky declination bands existed but were never tested.
The first entry of each tile list was not a tile but a global area: if its
sample count fell below ``tiling_min`` (default 100), tiling was suppressed and
a single untiled row was produced instead. Passing a *tuple* of tile lists
processed several tile sets in one call, chaining their indices through
``start_index``.

**Wiring status at removal.** The plumbing was complete from ``Record.add``
down through ``prep_row``, but nothing ever drove it: no ``Table.add``
implementation passed ``tiles=``, ``record.ring_tile_dict`` was assigned and
never read, and no host shipped a detailed label template. The feature could
not have worked even if called — the tile keys the tile tables actually used
(``where_all``, ``where_below``, ``where_between``, ``where_above``, ...) had
no ``FORMAT_DICT`` rows at all, so formatting a tiled row would have raised
``KeyError``. It emitted no tiled row in any shipped configuration.

**Reintroducing it.** Under the template-pull design the templates define the
column set, so a detailed variant is mostly a second template: add
``<HOST>_<kind>_detailed.lbl`` listing the per-pixel columns plus a tile-index
``COLUMN``, then restore the tile catalog, the ``tiles=`` path through
``Record.add``/``prep_row``, and the detailed table wiring in ``Suite`` and
``cumulative_support``. The removal commit in the template-pull PR carries the
full deleted code; because the repository squash-merges, retrieve it from the
pull request rather than from ``main``'s history.

API reference
=============

See :doc:`api/geometry_support` and :doc:`api/columns`.
