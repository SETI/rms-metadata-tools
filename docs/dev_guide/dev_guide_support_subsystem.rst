==============
Shared support
==============

Overview
========

Several modules are used by all three stages. They provide the base table class,
the global logger, label generation, the column-definition data, and a library
of utilities.

``common`` -- base class, logging, and CLI
==========================================

:mod:`metadata_tools.common` holds:

- :class:`~metadata_tools.common.Table`, the base class for every table kind
  (see :doc:`dev_guide_architecture`).
- The global :class:`pdslogger.PdsLogger`, obtained through
  :func:`~metadata_tools.common.get_logger` and configured per run by
  :func:`~metadata_tools.common.init_logger`. Library code logs through this
  logger; it never uses :mod:`logging` directly or bare ``print``.
- The shared argument parser
  :func:`~metadata_tools.common.get_common_args`, which the per-stage
  ``get_args`` functions extend. Its ``volume_arg`` / ``metadata_arg`` /
  ``output_arg`` parameters select which positional path arguments a stage takes,
  and :class:`~metadata_tools.common.PathAction` normalizes path separators while
  preserving URI prefixes.
- The cloud-task plumbing
  (:func:`~metadata_tools.common.add_task`,
  :func:`~metadata_tools.common.write_task_file`,
  :func:`~metadata_tools.common.task_source`) shared by the ``*_cloud.py``
  workers.

``label_support`` -- PDS3 labels
================================

:func:`~metadata_tools.label_support.create` generates a ``.lbl`` label for a
table by rendering the host's template (or a shared template from the global
``templates/`` directory) with ``rms-pdstemplate``. The inventory table uses no
table preprocessor; the other kinds use the PDS3 table preprocessor so column
definitions are validated against the data.

``columns`` -- geometry column definitions
==========================================

The :mod:`metadata_tools.columns` package assembles and re-exports the geometry
column-definition tables for the body, ring, sky, and sun tables (see
:doc:`api/columns`). The per-body dictionaries are built at import time by
substituting each body name into a placeholder
(:data:`~metadata_tools.defs.BODYX`) in the generic column lists. Because this
substitution runs at import, the ``oops`` body registry must already be
populated (see ``bodies`` below).

``bodies`` -- the oops body registry
====================================

:func:`~metadata_tools.bodies.get_bodies` builds the mapping from body name to
``oops`` ``Body`` object, including each primary's regular children, and
:data:`~metadata_tools.bodies.BODIES` is computed once on import. This requires
the host's ``oops`` module to have been initialized first (so SPICE bodies are
registered), which is why :mod:`metadata_tools.bodies` is excluded from the
hermetic test coverage and stubbed in the test fixtures.

``util`` and ``defs``
=====================

:mod:`metadata_tools.util` is the utility library: path helpers built on
``FCPath`` (:func:`~metadata_tools.util.select_dir`,
:func:`~metadata_tools.util.get_index_name`,
:func:`~metadata_tools.util.parse_template_name`,
:func:`~metadata_tools.util.get_volume_glob`), text-file read/write helpers that
work for local and remote paths, spacecraft-clock parsing/formatting, the
placeholder-substitution helpers used by the columns package
(:func:`~metadata_tools.util.replace`,
:func:`~metadata_tools.util.replacement_dict`), and the cyclic-range estimator
used by longitude columns.

:mod:`metadata_tools.defs` holds the constants: the planet name list
(:data:`~metadata_tools.defs.BODY_NAMES`), the ring-system radii, the global
template path, and the :data:`~metadata_tools.defs.BODYX` placeholder.

Invariants
==========

- **Paths.** Every file access goes through ``FCPath`` so local and remote
  storage are interchangeable; do not downcast to :class:`pathlib.Path` or
  :class:`str`. The package never creates directories through ``FCPath``.
- **Logging.** There is a single global logger; per-run handlers are added by
  :func:`~metadata_tools.common.init_logger`.
- **Import order.** :data:`~metadata_tools.bodies.BODIES` and the
  :mod:`metadata_tools.columns` tables are computed at import and depend on an
  initialized ``oops`` registry.

API reference
=============

See :doc:`api/core` and :doc:`api/columns`.
