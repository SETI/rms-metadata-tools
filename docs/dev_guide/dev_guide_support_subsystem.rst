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
- CLI argument helpers shared across all three stages.

``task_list_support`` -- cloud task files
=========================================

:mod:`metadata_tools.task_list_support` creates and writes the JSON task files
consumed by ``rms-cloud-tasks`` workers. The four public functions are:

- :func:`~metadata_tools.task_list_support.make_task` -- builds a single task
  dict for one volume ID.
- :func:`~metadata_tools.task_list_support.task_generator` -- yields one task
  dict per volume without touching the filesystem.
- :func:`~metadata_tools.task_list_support.scan_volumes` -- walks a directory
  tree and returns the sorted list of volume IDs it contains.
- :func:`~metadata_tools.task_list_support.write_task_file` -- writes the JSON
  task list for a volume list to a local or remote path.

``label_support`` -- PDS3 labels
================================

:func:`~metadata_tools.label_support.create` generates a ``.lbl`` label for a
table by rendering the host's template (or a shared template from the global
``templates/`` directory) with ``rms-pdstemplate``. The inventory template has
no COLUMN objects and uses no preprocessor; the other kinds chain four:
:func:`~metadata_tools.column_grammar.expand_format_references` expands the
format-dictionary references,
:func:`~metadata_tools.column_grammar.merge_column_definitions` lowers the
definition/stub column grammar to plain ``COLUMN`` objects, the PDS3 table
preprocessor validates the lowered columns against the data, and a strip step
sweeps any stray spec keyword so nothing non-PDS3 reaches a shipped label; see
:doc:`dev_guide_geometry_subsystem`.

``bodies`` -- the oops body registry
====================================

:func:`~metadata_tools.bodies.get_bodies` builds the mapping from body name to
``oops`` ``Body`` object, including each primary's regular children.
:func:`~metadata_tools.bodies.get_bodies_registry` returns a cached singleton (computed once
on first call). This requires the host's ``oops`` module to have been initialized
first (so SPICE bodies are registered), which is why :mod:`metadata_tools.bodies`
is excluded from the hermetic test coverage and stubbed in the test fixtures.

``util`` and ``defs``
=====================

:mod:`metadata_tools.util` is the utility library: path helpers built on
``FCPath`` (:func:`~metadata_tools.util.select_dir`,
:func:`~metadata_tools.util.get_index_name`,
:func:`~metadata_tools.util.parse_template_name`,
:func:`~metadata_tools.util.get_volume_glob`), text-file read/write helpers that
work for local and remote paths, spacecraft-clock parsing/formatting, the
placeholder-substitution helper used to bind a body name into a column's
backplane key (:func:`~metadata_tools.util.replace`), and the cyclic-range
estimator used by longitude columns.

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
- **Process-local state.** The module-level caches (the resolved label schemas
  in ``geometry_support.label_schema``, the mission table in
  ``geometry_support.formats``, the ``bodies`` registry) and the
  :mod:`metadata_tools.config` host registry are plain globals with no locking.
  The package is not thread-safe; parallel runs use separate processes (the
  cloud Worker spawns them), each with its own copies.
- **Import order.** The :func:`~metadata_tools.bodies.get_bodies_registry`
  singleton is built on its first call and requires an initialized ``oops``
  registry, so the host's ``host_init`` must have run first.

API reference
=============

See :doc:`api/core` and :doc:`api/task_list_support`.
