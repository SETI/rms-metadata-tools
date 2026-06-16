============
Architecture
============

Engine and host configuration
=============================

The codebase has two halves. The **engine** (``src/metadata_tools/``, excluding
``hosts/``) is host-agnostic: it knows how to walk a volume tree, read labels,
compute geometry, format columns, and write tables and PDS3 labels. A **host
configuration** package (``src/metadata_tools/hosts/<HOST>/``) supplies the
collection-specific knowledge: which files to include, how to derive certain
columns, the spacecraft ID, the body-selection mission table, the meshgrids, and
the label templates.

The engine never imports a specific host. Instead, the host's runnable scripts
set the current working directory to the host package and import their
configuration as the top-level modules ``host_config``, ``index_config``, and
``geometry_config``; the engine modules then import those same top-level names.
This is why host scripts only work when run from inside the host directory, and
why the documentation build mocks those three module names (see ``docs/conf.py``).

Table classes
=============

All table kinds derive from a single base class. The geometry tables for one
volume are coordinated by a :class:`~metadata_tools.geometry_support.suite.Suite`,
which builds one :class:`~metadata_tools.geometry_support.record.Record` per
observation and feeds it to each table.

.. mermaid::

   classDiagram
       class Table {
           +template_path
           +volume_id
           +level
           +qualifier
           +rows
           +filename
           +write(labels_only)
       }
       class IndexTable {
           +create(labels_only, pattern)
           +add(root, name)
       }
       class InventoryTable {
           +add(record)
       }
       class SkyTable {
           +add(record)
       }
       class SunTable {
           +add(record)
       }
       class RingTable {
           +add(record)
       }
       class BodyTable {
           +add(record)
       }
       class Suite {
           +tables
           +create(labels_only, pattern)
           +make_records(index)
           +add(records)
           +write(labels_only)
       }
       class Record {
           +primary
           +bodies
           +backplane
           +add(qualifier)
           +postprocess(columns, qualifier)
       }

       Table <|-- IndexTable
       Table <|-- InventoryTable
       Table <|-- SkyTable
       Table <|-- SunTable
       Table <|-- RingTable
       Table <|-- BodyTable
       Suite o-- Table : owns
       Suite ..> Record : produces
       BodyTable ..> Record : consumes

The base class
--------------

:class:`~metadata_tools.common.Table` holds the state common to every table: the
label ``template_path``, the ``volume_id``, the processing ``level``
(``"summary"``, ``"detailed"``, or ``"index"``), the ``qualifier`` (``"sky"``,
``"sun"``, ``"ring"``, ``"body"``, ``"inventory"``, or ``"supplemental"``), the
accumulated ``rows``, and the output ``filename``. Its
:meth:`~metadata_tools.common.Table.write` method writes the table file (unless
``labels_only`` is set) and then generates the PDS3 label through
:func:`~metadata_tools.label_support.create`. Subclasses add the logic that
fills ``rows``.

The index table
---------------

:class:`~metadata_tools.index_support.IndexTable` represents one volume's
supplemental index. :meth:`~metadata_tools.index_support.IndexTable.create`
iterates the volume's data labels, and
:meth:`~metadata_tools.index_support.IndexTable.add` reads each PDS3 label and
appends one formatted row. Its columns come from the supplemental label
template, not from a Python column list. It does not use a
:class:`~metadata_tools.geometry_support.record.Record`.

The geometry tables
-------------------

The five geometry tables in
:mod:`metadata_tools.geometry_support.tables` all extend
:class:`~metadata_tools.common.Table` and share a single contract: an ``add``
method that takes a :class:`~metadata_tools.geometry_support.record.Record` and
appends the appropriate rows.
:class:`~metadata_tools.geometry_support.tables.SkyTable`,
:class:`~metadata_tools.geometry_support.tables.SunTable`,
:class:`~metadata_tools.geometry_support.tables.RingTable`, and
:class:`~metadata_tools.geometry_support.tables.BodyTable` each ask the record
for the rows for their qualifier (the body table emits one row per selected
body; the ring table emits rows only when a ring system is present), while
:class:`~metadata_tools.geometry_support.tables.InventoryTable` writes the list
of bodies in the field of view as a CSV row.

The volume coordinator
----------------------

:class:`~metadata_tools.geometry_support.suite.Suite` is the geometry stage's
per-volume coordinator. It is *not* a table; it owns a list of table objects
(one inventory table plus a sky, ring, and body table per requested level),
reads the volume's observations through the host's ``from_index`` hook, builds
the meshgrids, and in
:meth:`~metadata_tools.geometry_support.suite.Suite.create` loops over
observations, building records with
:meth:`~metadata_tools.geometry_support.suite.Suite.make_records` and dispatching
them to every table with
:meth:`~metadata_tools.geometry_support.suite.Suite.add`.

The row builder
---------------

:class:`~metadata_tools.geometry_support.record.Record` represents one
observation across all geometry tables. On construction it determines the
primary body from the spacecraft clock (via
:func:`~metadata_tools.geometry_support.bodies_select.get_primary`), selects the
bodies in the field of view, and builds the ``oops`` backplane. Its
:meth:`~metadata_tools.geometry_support.record.Record.add` method delegates to
:func:`~metadata_tools.geometry_support.prep.prep_row` to evaluate and format
the columns for a qualifier, then
:meth:`~metadata_tools.geometry_support.record.Record.postprocess` applies the
inter-column null-linking rules.

Data flow
=========

The three stages connect through files on disk, not in-memory objects:

#. The index stage (:func:`~metadata_tools.index_support.process_index`) writes a
   supplemental index table per volume.
#. The geometry stage
   (:func:`~metadata_tools.geometry_support.process.process_tables`) reads each volume's
   supplemental index, builds a
   :class:`~metadata_tools.geometry_support.suite.Suite`, and writes the geometry
   tables.
#. The cumulative stage
   (:func:`~metadata_tools.cumulative_support.create_cumulative_indexes`) walks
   the tree and concatenates the per-volume tables.

Each stage is documented in its own chapter:
:doc:`dev_guide_index_subsystem`, :doc:`dev_guide_geometry_subsystem`, and
:doc:`dev_guide_cumulative_subsystem`. The shared machinery is covered in
:doc:`dev_guide_support_subsystem`.
