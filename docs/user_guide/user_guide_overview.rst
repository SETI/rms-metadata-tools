========
Overview
========

Purpose
=======

The Planetary Data System (PDS) distributes planetary science data as
*collections* (also called volumes). Alongside the data products themselves,
each collection ships **metadata tables**: flat ASCII tables in which every row
describes one data product (for example, one image), together with a PDS3
*label* that documents the columns. ``rms-metadata-tools`` (the importable
package ``metadata_tools``) generates these tables and labels for the PDS
Ring-Moon Systems Node at the SETI Institute.

The tables feed two consumers: the `OPUS <https://opus.pds-rings.seti.org>`_
search service, which indexes their columns so users can search a collection by
observation time, geometry, instrument settings, and so on; and ordinary PDS
users, who download the supplemental tables directly.

The package generates three kinds of table, described below. They are the
distinguishing feature of the tool: rather than hand-editing tables, you
describe a collection once (its label template and a small configuration
module) and the tool produces consistent, label-validated output for an entire
volume tree.

Table kinds
===========

The three table kinds are generated in this order, because each builds on the
output of the previous one.

**Index tables** (*supplemental index files*)
    Extra columns added to a project's corrected index file, drawn from each
    data product's PDS3 label or derived from label quantities. Index tables
    have the same structure as the corrected index files they supplement, so
    they can be merged back in when a host's ``from_index`` method reads a
    collection. Index tables are produced by
    :func:`~metadata_tools.index_support.process_index`.

**Geometry tables**
    Geometric quantities (positions, angles, ranges, and resolutions for
    bodies, rings, the sky, and the Sun) computed from SPICE through the
    ``oops`` library, using pointing taken from the index table or the PDS3
    label. Each observation yields a *summary* table (one row per observation)
    and, optionally, a *detailed* table (one row per spatial subregion, or
    "tile"). Geometry tables are produced by
    :func:`~metadata_tools.geometry_support.process.process_tables`.

**Cumulative tables**
    Concatenations of the per-volume index and geometry tables across a whole
    volume tree, with a matching label. Cumulative tables are produced by
    :func:`~metadata_tools.cumulative_support.create_cumulative_indexes`.

Workflow
========

For a single collection the workflow is a three-stage pipeline. Each stage is a
command-line program that you run from inside the collection's host directory
(see :doc:`user_guide_installation`):

.. mermaid::

   flowchart TD
       L[PDS3 data labels<br/>+ corrected index file] --> I[Stage 1: index<br/>HOST_index.py]
       I --> IT[(Supplemental<br/>index table + label)]
       IT --> G[Stage 2: geometry<br/>HOST_geometry.py]
       SPICE[SPICE kernels<br/>via oops] --> G
       G --> GT[(Geometry tables<br/>summary/detailed + labels)]
       IT --> C[Stage 3: cumulative<br/>HOST_cumulative.py]
       GT --> C
       C --> CT[(Cumulative tables + labels)]

1. **Index** reads each data product's PDS3 label and writes a supplemental
   index table for every volume in the tree.
2. **Geometry** reads the supplemental index table for each volume, computes the
   geometry backplanes with ``oops``, and writes the summary (and optionally
   detailed) geometry tables.
3. **Cumulative** walks the whole tree and concatenates the per-volume index and
   geometry tables into cumulative tables.

Each stage writes a ``.tab`` (or ``.csv`` for the inventory) data file plus a
``.lbl`` PDS3 label generated from the host's label template.

For how each program is invoked and what options it accepts, see
:doc:`user_guide_index`, :doc:`user_guide_geometry`, and
:doc:`user_guide_cumulative`. For distributing the work across many machines on
Google Cloud, see :doc:`user_guide_cloud`.
