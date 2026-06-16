============
Introduction
============

Audience
========

This guide assumes a competent Python developer who is new to *this* codebase.
It favors architecture and contracts over restating what the code already says.
If you only want to install the package and run it against an existing
collection, read the :doc:`/user_guide/user_guide` instead; this guide is about
working on the code.

What the package does
=====================

``rms-metadata-tools`` (importable as ``metadata_tools``) generates PDS3 index,
geometry, and cumulative metadata tables, and their PDS3 labels, for planetary
science data collections at the PDS Ring-Moon Systems Node. Each row of a table
holds the metadata for one data product. The :doc:`/user_guide/user_guide_overview`
describes the three table kinds and the pipeline that produces them.

Runtime and key dependencies
============================

The package targets **Python 3.11+**. Its principal dependencies are:

- ``rms-oops`` — the geometry/SPICE engine that computes backplanes; the
  geometry stage is built on it.
- ``rms-filecache`` — the ``FCPath`` path abstraction used for every file
  access, so local and remote (``gs://``, ``s3://``) storage are interchangeable.
- ``rms-pdstemplate`` — renders PDS3 labels from templates.
- ``rms-pdsparser`` and ``rms-pdstable`` — read PDS3 labels and tables.
- ``rms-pdslogger`` — structured logging through the package's global logger.
- ``rms-julian``, ``rms-vicar``, ``cspyce``, and ``fortranformat`` — time
  conversion, VICAR labels, SPICE clock conversion, and Fortran-style numeric
  formatting.
- ``rms-cloud-tasks`` (optional) — distributes per-volume work across GCP.

Design in one sentence
======================

A host-agnostic **engine** under ``src/metadata_tools/`` does the work; each
supported collection contributes a small **host configuration** package under
``src/metadata_tools/hosts/<HOST>/`` that plugs into the engine. The split is
the central idea of the codebase, and is the subject of
:doc:`dev_guide_architecture` and :doc:`dev_guide_extending`.
