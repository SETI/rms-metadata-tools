============================
Distributed (cloud) runs
============================

Generating geometry for a large collection is CPU-bound and embarrassingly
parallel across volumes. Two families of console scripts handle this:

**Worker scripts** — run the engine locally in parallel (no GCP account needed):

.. code-block:: text

   metadata-index-worker    HOST_ID [options] volume_tree metadata_tree output_tree
   metadata-geometry-worker HOST_ID [options] metadata_tree output_tree
   metadata-cumulative-worker HOST_ID [options] output_dir

**Cloud scripts** — dispatch work to GCP (``--config`` defaults to the host's
``cloud/<HOST>/gcp_*_config.yml``):

.. code-block:: text

   metadata-index-cloud    HOST_ID [options] volume_tree metadata_tree output_tree
   metadata-geometry-cloud HOST_ID [options] metadata_tree output_tree
   metadata-cumulative-cloud HOST_ID [options] output_dir

Both families require the ``cloud`` optional dependency group:

.. code-block:: bash

   pip install -e ".[cloud]"

How it works
============

The worker and cloud scripts reuse the same engine entry points
(:func:`~metadata_tools.index_support.process_index`,
:func:`~metadata_tools.geometry_support.process.process_tables`) but run them
inside a ``rms-cloud-tasks`` Worker.

Worker scripts start a local Worker directly. Cloud scripts shell out to
``cloud_tasks run``, which provisions GCP instances, generates and delivers a
startup script to each VM, and monitors progress. The startup script
pip-installs ``rms-metadata-tools`` from PyPI (or clones a specific git branch
when ``--debug-branch`` / ``$GCP_DEBUG_BRANCH`` is set) and then runs the
appropriate worker command.

Local parallel runs
====================

Run a worker script just like its plain counterpart, with the additional
``--num-simultaneous-tasks`` option to process volumes in parallel:

.. code-block:: bash

   metadata-index-worker GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --num-simultaneous-tasks 12

You can also restrict to specific volumes with ``--volumes``:

.. code-block:: bash

   metadata-geometry-worker GO_0xxx "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --volumes GO_0017 GO_0018

GCP runs
========

For a GCP run, pass the same path arguments as a local run and add ``--config``.
When ``--config`` is omitted, each dispatch command defaults to the conventional
``cloud/<HOST>/gcp_<index|geometry|cumulative>_config.yml`` if that file exists.
The GCP instance startup script is generated automatically from those arguments
at dispatch time, so no personal bucket paths ever appear in committed files.

The recommended workflow is one directory per dispatch, outside the repository:
generate the task file there, then dispatch from it, so the task DB and any
status dumps land beside the task list. ``--task-file`` defaults to
``./tasks.json``, so no flags are needed:

.. code-block:: bash

   gcloud auth application-default login        # if necessary

   mkdir -p ~/metadata-runs/2026-08-21-GO-index && cd ~/metadata-runs/2026-08-21-GO-index

   # Generate the task file into the run directory (default output: ./tasks.json)
   metadata-task-list GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/"

   # Dispatch to GCP (--config and --task-file use their defaults)
   metadata-index-cloud GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/" "$RMS_METADATA_GCP/GO_0xxx/" \
       "$RMS_METADATA_TEST_GCP/GO_0xxx/" --use-spot

Or pass ``--volumes`` directly and let the cloud script generate the task file
automatically:

.. code-block:: bash

   metadata-index-cloud GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/" "$RMS_METADATA_GCP/GO_0xxx/" \
       "$RMS_METADATA_TEST_GCP/GO_0xxx/" --use-spot --volumes GO_0022 GO_0016

Both flags can always be given explicitly (taking precedence over the defaults),
e.g. ``--config my_gcp_config.yml --task-file ./retry_tasks.json``.

The ``gcp_*_config.yml`` machine/queue configuration files live in
``cloud/<HOST>/`` at the repository root (not inside the installed package).
The instance startup script is generated at dispatch time and delivered to
``cloud_tasks`` via the config YAML; it is not stored on disk.

Each host carries two config tiers. The default (unsuffixed)
``gcp_<type>_config.yml`` files describe a small single-instance setup for
testing; the ``gcp_<type>_prod_config.yml`` files are tuned for throughput
over the full collection (multi-instance spot fleets sized so the whole task
queue runs in one wave, per-stage runtimes and boot-disk sizing, preemption
retry, and a price cap). Select a production config explicitly:

.. code-block:: bash

   metadata-index-cloud GO_0xxx <paths...> --use-spot \
       --config gcp_index_prod_config.yml --task-file ./tasks.json

Previewing the startup script
------------------------------

To see exactly what startup script would be sent to a GCP instance without
actually dispatching, use ``--create-startup-file``:

.. code-block:: bash

   metadata-index-cloud GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/" "$RMS_METADATA_GCP/GO_0xxx/" \
       "$RMS_METADATA_TEST_GCP/GO_0xxx/" --create-startup-file startup.sh

This writes the startup script to ``startup.sh`` and exits immediately. The
``--config`` flag is not required when ``--create-startup-file`` is used.

Worker options
==============

Worker scripts accept all options of their non-cloud counterpart, plus:

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Option
     - Description
   * - ``--task-file FILE``
     - Path to a task file (JSON). Passed automatically when using
       ``metadata-task-list`` output; can also be provided manually.
   * - ``--num-simultaneous-tasks N``
     - Number of volumes to process in parallel.

Cloud options
=============

Cloud scripts accept all options of their non-cloud counterpart, plus the
following. Options in the first group are forwarded to ``cloud_tasks run``;
options in the second group are consumed before dispatch and never reach
``cloud_tasks`` or the worker.

Dispatch options (forwarded to ``cloud_tasks run``):

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Option
     - Description
   * - ``--config FILE``
     - GCP configuration YAML. Defaults to the conventional
       ``cloud/<HOST>/gcp_<type>_config.yml`` when that file exists. Bare
       filenames are resolved against the ``cloud/<HOST>/`` directory.
   * - ``--task-file FILE``
     - Path to a task file (JSON). Defaults to ``./tasks.json`` when that
       exists in the current directory and no ``--volumes`` or ``--continue``
       is given. Bare filenames resolve against ``cloud/<HOST>/``; use a
       ``./`` prefix (or an absolute path) to select a file relative to the
       current directory.
   * - ``--use-spot``
     - Request spot (preemptible) GCP instances.

Cloud-only overrides (consumed before dispatch):

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Option
     - Description
   * - ``--create-startup-file FILE``
     - Write the generated startup script to ``FILE`` and exit without
       dispatching. ``--config`` is not required when this flag is used.
   * - ``--startup-template FILE``
     - Use ``FILE`` as the startup script template instead of the default
       ``cloud/gcp_common_startup.sh``. Overrides ``$GCP_STARTUP_TEMPLATE``.
   * - ``--oops-resources NAME``
     - Name of the persistent GCP disk to attach as OOPS resources on each VM.
       Overrides ``$OOPS_RESOURCES_DISK``. One of this flag or the environment
       variable is required.
   * - ``--service-account ACCOUNT``
     - GCP service account to use for dispatch. Overrides ``$GCP_SERVICE_ACCOUNT``.
   * - ``--debug-branch BRANCH``
     - Git branch to clone on GCP VMs instead of pip-installing from PyPI.
       Overrides ``$GCP_DEBUG_BRANCH``. Use for testing unreleased changes.

Environment variables
=====================

Cloud-related settings can be provided via environment variables, which are
loaded from a ``.env`` file at the repository root at import time (shell
environment takes precedence over ``.env``). The file is git-ignored so it
never contains committed credentials.

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Variable
     - Description
   * - ``GCP_SERVICE_ACCOUNT``
     - GCP service account passed to ``cloud_tasks run`` via ``--service-account``.
       Overridden by the ``--service-account`` CLI flag.
   * - ``OOPS_RESOURCES_DISK``
     - Name of the persistent disk to attach on each GCP VM for OOPS resources.
       Injected as ``$OOPS_RESOURCES_DISK`` in the startup script header.
       Overridden by ``--oops-resources``. Required — either this variable or
       that flag must be set.
   * - ``GCP_STARTUP_TEMPLATE``
     - Path to a custom startup script template to use instead of
       ``cloud/gcp_common_startup.sh``. Overridden by ``--startup-template``.
       Leave blank or unset to use the default.
   * - ``GCP_DEBUG_BRANCH``
     - Git branch to clone on GCP VMs. When unset and ``--debug-branch`` is not
       given, the startup script pip-installs ``rms-metadata-tools`` from PyPI
       instead of cloning. Overridden by ``--debug-branch``.

A typical ``.env`` file:

.. code-block:: bash

   # GCP service account to pass to cloud_tasks run (--service-account).
   GCP_SERVICE_ACCOUNT=rms-metadata-tools-154@rms-metadata.iam.gserviceaccount.com

   # Name of the persistent disk to attach on each GCP VM for OOPS resources.
   OOPS_RESOURCES_DISK=standard-oops-resources-central1-a-1

   # Custom startup template (leave blank to use the default).
   GCP_STARTUP_TEMPLATE=

   # Git branch to clone on GCP VMs (leave blank to pip-install from PyPI).
   GCP_DEBUG_BRANCH=

The ``metadata-task-list`` script
==================================

``metadata-task-list`` generates a task file without doing any processing. It
supports two modes:

**Scan mode** — walk a volume tree and create one task per discovered volume:

.. code-block:: text

   metadata-task-list HOST_ID tree [--output FILE]

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
     - Output JSON task file path, relative to the current directory. Defaults
       to ``./tasks.json``, which the ``metadata-*-cloud`` commands pick up as
       the default ``--task-file``.

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
