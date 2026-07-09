============================
Distributed (cloud) runs
============================

Generating geometry for a large collection is CPU-bound and embarrassingly
parallel across volumes. Three cloud console scripts distribute the per-volume
work using the `rms-cloud-tasks <https://pypi.org/project/rms-cloud-tasks>`_
framework on Google Cloud Platform (GCP):

.. code-block:: text

   metadata-index-cloud    HOST_ID [options] volume_tree metadata_tree output_tree
   metadata-geometry-cloud HOST_ID [options] metadata_tree output_tree
   metadata-cumulative-cloud HOST_ID [options] output_dir

These scripts require the ``cloud`` optional dependency group:

.. code-block:: bash

   pip install -e ".[cloud]"

How it works
============

The cloud scripts reuse the same engine entry points
(:func:`~metadata_tools.index_support.process_index`,
:func:`~metadata_tools.geometry_support.process.process_tables`) but run them
inside a ``rms-cloud-tasks`` Worker.

- Without ``--config`` the script behaves identically to its non-cloud
  counterpart, except that ``--num-simultaneous-tasks`` is also accepted to
  run volumes in parallel locally.
- With ``--config`` the script shells out to ``cloud_tasks run`` for a full GCP
  dispatch instead of running locally.

Local parallel runs
====================

Run a cloud script exactly like its plain counterpart, with the additional
``--num-simultaneous-tasks`` option to process volumes in parallel:

.. code-block:: bash

   metadata-index-cloud GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --num-simultaneous-tasks 12

You can also restrict to specific volumes with ``--volumes``:

.. code-block:: bash

   metadata-geometry-cloud GO_0xxx "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --volumes GO_0017 GO_0018

GCP runs
========

For a GCP run, use the same path arguments as a local run and add ``--config``.
The GCP instance startup script is generated automatically from those arguments
at dispatch time, so no personal bucket paths ever appear in committed files.

First generate a task file with ``metadata-task-list``, then dispatch:

.. code-block:: bash

   gcloud auth application-default login        # if necessary

   # Generate task file
   metadata-task-list GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/" --output tasks.json

   # Dispatch to GCP (same paths as local; --config triggers GCP dispatch)
   metadata-index-cloud GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/" "$RMS_METADATA_GCP/GO_0xxx/" \
       "$RMS_METADATA_TEST_GCP/GO_0xxx/" --use-spot \
       --config cloud/GO_0xxx/gcp_index_config.yml \
       --task-file tasks.json

Or pass ``--volumes`` directly and let the cloud script generate the task file
automatically:

.. code-block:: bash

   metadata-index-cloud GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/" "$RMS_METADATA_GCP/GO_0xxx/" \
       "$RMS_METADATA_TEST_GCP/GO_0xxx/" --use-spot \
       --config cloud/GO_0xxx/gcp_index_config.yml \
       --volumes GO_0022 GO_0016

The ``gcp_*_config.yml`` machine/queue configuration files live in
``cloud/<HOST>/`` at the repository root (not inside the installed package).
The instance startup script is generated at dispatch time and not stored on disk.

Cloud options
=============

The cloud scripts accept all options of their non-cloud counterpart, plus:

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Option
     - Description
   * - ``--config FILE``
     - GCP configuration YAML. When present, the script dispatches to GCP
       instead of running locally. Bare filenames are resolved against the
       ``cloud/<HOST>/`` directory.
   * - ``--task-file FILE``
     - Path to a task file (JSON). Passed automatically when using
       ``metadata-task-list`` output; can also be provided manually.
   * - ``--use-spot``
     - Request spot (preemptible) GCP instances.
   * - ``--num-simultaneous-tasks N``
     - Number of volumes to process in parallel (local runs only).

The ``metadata-task-list`` script
==================================

``metadata-task-list`` generates a task file without doing any processing. It
supports two modes:

**Scan mode** — walk a volume tree and create one task per discovered volume:

.. code-block:: text

   metadata-task-list HOST_ID tree --output FILE

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Argument / option
     - Description
   * - ``HOST_ID``
     - Host identifier (e.g. ``GO_0xxx``).
   * - ``tree``
     - Path to the top of the volume or metadata tree to scan.
   * - ``--output FILE``, ``-o``
     - Output JSON task file path. Required. A bare filename is resolved against
       the host's directory.

**Explicit mode** — list volumes directly (no HOST_ID):

.. code-block:: text

   metadata-task-list --volumes VOL [VOL ...] --output FILE

The output file is always a JSON array with one object per volume; see "Task
file schema" below.

Task file schema
================

The task file is JSON: a list of task objects, one per volume. Each object has a
unique ``task_id`` and a ``data`` payload carrying the volume ID that the worker
passes back to the engine:

.. code-block:: json

   [
     {
       "task_id": "geometry-task-GO_0017",
       "data": { "volume_id": "GO_0017" }
     },
     {
       "task_id": "geometry-task-GO_0018",
       "data": { "volume_id": "GO_0018" }
     }
   ]

The ``task_id`` prefix identifies the stage that produced the file. The worker
reads each entry, invokes the engine for ``data.volume_id``, and reports success
or failure back to ``rms-cloud-tasks``.
