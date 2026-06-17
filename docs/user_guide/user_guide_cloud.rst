============================
Distributed (cloud) runs
============================

Generating geometry for a large collection is CPU-bound and embarrassingly
parallel across volumes. Each host therefore ships ``*_cloud.py`` counterparts
to the three programs (``<HOST>_index_cloud.py``, ``<HOST>_geometry_cloud.py``,
``<HOST>_cumulative_cloud.py``) that distribute the per-volume work using the
`rms-cloud-tasks <https://pypi.org/project/rms-cloud-tasks>`_ framework on
Google Cloud Platform (GCP).

These workers require the ``cloud`` optional dependencies:

.. code-block:: bash

   pip install -e ".[cloud]"

How it works
============

The cloud programs reuse the same engine entry points
(:func:`~metadata_tools.index_support.process_index`,
:func:`~metadata_tools.geometry_support.process.process_tables`) in two modes:

1. **Build a task list.** Running the program with ``--task-output`` (or letting
   the worker build it) produces a task file: one task per volume. No tables are
   generated in this mode.
2. **Process tasks.** A worker pool consumes the task file, calling the engine
   once per volume with the volume ID from each task.

Local parallel runs
====================

Run a cloud program exactly like its plain counterpart, with additional
``rms-cloud-tasks`` worker options such as ``--num-simultaneous-tasks``:

.. code-block:: bash

   cd src/metadata_tools/hosts/GO_0xxx
   python GO_0xxx_index_cloud.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --num-simultaneous-tasks 12

GCP runs
========

For a run on GCP, authenticate, generate the task file, and submit it with the
host's paired configuration:

.. code-block:: bash

   gcloud auth application-default login        # if necessary

   python GO_0xxx_index_cloud.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" -to index_tasks.json
   cloud_tasks run --config gcp_index_config.yml --task-file index_tasks.json --use-spot

Each host directory contains the ``gcp_*_config.yml`` machine/queue
configuration and the ``gcp_*_startup.sh`` instance start-up script referenced
above.

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
