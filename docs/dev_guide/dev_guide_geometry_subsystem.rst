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
meshgrids once, and builds the table list: an inventory table plus the sky,
ring, and body tables. It loops over observations, building one
:class:`~metadata_tools.geometry_support.record.Record` each and dispatching it
to every table. A ``RuntimeError`` is raised if a volume contains more than one
index file.

Record and prep
===============

:class:`~metadata_tools.geometry_support.record.Record` holds one observation's
state: the primary body (from
:func:`~metadata_tools.geometry_support.bodies_select.get_primary`), the selected
bodies, and the ``oops`` backplane. Each table passes its own resolved columns
to :meth:`~metadata_tools.geometry_support.record.Record.add`, which binds the
``BODYX`` placeholder to the body being written and calls
:func:`~metadata_tools.geometry_support.prep.prep_row`, which evaluates each
column's backplane key, applies the excluded-pixel mask, and formats the result;
:meth:`~metadata_tools.geometry_support.record.Record.postprocess` then applies
each link function to its group of linked columns.

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
valid-range clipping, and overflow. It is driven entirely by the column's label
stubs, which supply the field width, print format, overflow format, derived
unit-conversion flag, null value, and valid range -- all read from the label
template.

Where a column's metadata comes from
====================================

The **label template** is the single source of truth for a geometry column,
declared in the definition/stub grammar of
:mod:`metadata_tools.column_grammar`: each computed column is one
``COLUMN_DEFINITION`` object -- carrying the computation spec, the label
metadata shared by the column's values, and the shared lead-in
``DESCRIPTION`` -- followed by one ``COLUMN_STUB`` object per value, carrying
its ``NAME``, any keyword it overrides, and its own ``DESCRIPTION``, which
continues the definition's. A single-valued column is simply a plain
``COLUMN`` carrying its own spec keywords. Group size is the stub count;
membership is declared by the stub's own object type, so no column can be
assimilated into a group by accident.

.. code-block:: text

     OBJECT                        = COLUMN_DEFINITION
       NAME                        = "RING_RADIUS"
       FORMAT                      = "F12.3"
       OVERFLOW_FORMAT             = "E12.5"
       UNIT                        = "km"
       NULL_CONSTANT               = -999.
       BACKPLANE_KEY               = ('ring_radius', 'bodyx:RING')
       MASK                        = ('PM', 'P', '')
       DESCRIPTION                 = "Ring radius is the distance from ..."
     END_OBJECT                    = COLUMN_DEFINITION

     OBJECT                        = COLUMN_STUB
       NAME                        = "MINIMUM_RING_RADIUS"
       DESCRIPTION                 = "This column tabulates the minimum ..."
     END_OBJECT                    = COLUMN_STUB

     OBJECT                        = COLUMN_STUB
       NAME                        = "MAXIMUM_RING_RADIUS"
       DESCRIPTION                 = "This column tabulates the maximum ..."
     END_OBJECT                    = COLUMN_STUB

The spec keywords, allowed on definitions only (except ``OVERFLOW_FORMAT``,
which a stub may override like ``FORMAT``):

* ``BACKPLANE_KEY`` -- the key handed to ``Backplane.evaluate()``, as a Python
  tuple literal. The token ``'bodyx'`` (:data:`~metadata_tools.defs.BODYX`) is
  substituted per body at row time, and a string of the form
  ``'defs.<DICT>["bodyx"]'`` resolves to a ``defs`` dictionary lookup after
  substitution.
* ``MASK`` (default ``('', '', '')``) -- the ``(masker, shadower, face)``
  codes. The masker/shadower strings concatenate ``"P"`` (planet), ``"R"``
  (rings), and ``"M"`` (blocker body); the face is ``"D"``, ``"N"``, or ``""``.
* ``OVERFLOW_FORMAT`` -- the fallback format substituted when a value will not
  fit its field, in the same PDS3 FORMAT notation as ``FORMAT`` itself. It
  must fill the field exactly.
* ``LINK_FN`` / ``LINK_ID`` -- a postprocessing function applied jointly to a
  group of columns, and the token naming the group. The id is an arbitrary
  string whose only meaning is equality: columns in one table sharing
  ``(LINK_FN, LINK_ID)`` form one group. ``'null'`` -- which nulls the whole
  group when any member is null -- is the one link function defined so far; a
  new one is added to the dispatch table in
  :meth:`~metadata_tools.geometry_support.record.Record.postprocess` and to
  the known-function set in
  :mod:`~metadata_tools.geometry_support.label_schema`.

The right-hand side of ``BACKPLANE_KEY`` and ``MASK`` is a Python literal on a
single line, parsed with :func:`ast.literal_eval`; nothing ever parses these
lines as ODL. Neither block kind nor any spec keyword is PDS3:
:func:`~metadata_tools.label_support.create` lowers every group to plain
``COLUMN`` objects (via
:func:`~metadata_tools.column_grammar.merge_column_definitions`) before a
label is generated, so shipped labels are indistinguishable from hand-written
ones. Descriptions *compose*: a shipped column's ``DESCRIPTION`` is the
definition's shared lead-in followed by the stub's per-value prose, so the
lead-in is written once per quantity while each extreme keeps its own
paragraph. Either side may also stand alone -- a stub with no description
ships the definition's, and vice versa.

This is the same arrangement as the index pipeline, where
:class:`~metadata_tools.index_support.table.IndexTable` derives its columns from
its own template -- here the template also carries the computation, so a host
can define a column end to end with no engine edit.

Label schema pull
=================

:func:`~metadata_tools.geometry_support.label_schema.resolve_schema` parses a
host's summary template: a leading run of plain ``COLUMN`` objects with no
``BACKPLANE_KEY`` must match the table kind's fixed prefix columns
(``VOLUME_ID``, ``FILE_SPECIFICATION_NAME``, and, per table kind,
``SYSTEM_NAME`` and ``BODY_NAME``); the rest of the table is self-contained
single columns and definition/stub groups. Template order is output order. The result is cached per (template directory,
qualifier) and resolved once, when the table is constructed.

Removing a column removes its computation with it: delete a definition and
its stubs from the shared fragment and nothing else. (A host that must
diverge from the collection-independent column set shadows a fragment with
its own copy in its ``templates/`` directory, which ``$INCLUDE`` resolution
finds first.) Malformed shapes are errors, all raised at construction rather
than allowed to misalign a row per observation:

* a stub with no preceding definition, or a definition with no stubs;
* more than two stubs (no computation produces more than two values);
* a plain ``COLUMN`` among the groups, or a spec keyword on a prefix column
  or a stub;
* a definition with no ``BACKPLANE_KEY``, a malformed spec literal, or a
  duplicated keyword;
* only one of ``LINK_FN`` and ``LINK_ID``, or an unknown link function;
* an ``OVERFLOW_FORMAT`` that does not fill its field exactly;
* a column with no null keyword, or with no ``FORMAT``;
* ``VALID_MINIMUM == VALID_MAXIMUM``, which would null every value.

Because nothing exercises the generated tables by default -- the end-to-end
comparisons are archive-gated -- ``tests/test_geometry_schema.py`` is the
guard that the shipped templates keep resolving to the expected shape.

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
when SPICE pointing is unavailable, clears the record's ``pointing_available``
flag. :func:`~metadata_tools.geometry_support.prep.prep_row` then nulls every
column, and because the row is all-null it is dropped (``allow_zero_rows``
defaults to True and no caller overrides it): such an observation gets an
inventory row with an empty body list but no summary-table rows.

Important invariants
====================

- **Units.** Backplane values are in radians; columns whose derived flag is
  ``"DEG"``, ``"360"``, or ``"-180"`` are converted to degrees by
  :func:`~metadata_tools.geometry_support.formatting.formatted_column`. Do not
  pre-convert. The flag is derived from each column's ``UNIT``, valid range,
  and ``DATA_TYPE``, never stated directly.
- **Column specifications.** A
  :class:`~metadata_tools.geometry_support.label_schema.ResolvedColumn`
  carries the backplane key, the mask, the link fields, and one
  :class:`~metadata_tools.geometry_support.label_schema.ColumnStub` per value
  it produces -- all of it parsed from the label template.
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

See :doc:`api/geometry_support`.
