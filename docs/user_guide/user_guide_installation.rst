======================
Installation and setup
======================

Supported Python versions
=========================

``rms-metadata-tools`` requires **Python 3.11 or later** and is tested on
Python 3.11, 3.12, and 3.13. It runs on Linux, macOS, and Windows.

Prerequisites
=============

The geometry stage computes quantities from SPICE through the ``rms-oops``
library. Generating geometry tables therefore requires:

- The SPICE kernels for the spacecraft and bodies in your collection, installed
  where ``oops`` can find them. The host's initialization step (for example
  ``oops.hosts.galileo.ssi.initialize()``) loads them.
- The data volume tree and the project-supplied *corrected* index files for the
  collection.

The index stage needs only the PDS3 data labels and the corrected index file;
it does not require SPICE.

Installation
============

The package and its runtime dependencies are published on PyPI as
``rms-metadata-tools``:

.. code-block:: bash

   pip install rms-metadata-tools

To work from a checkout (recommended when you are adding or modifying a host
configuration, since the runnable host scripts live in the source tree):

.. code-block:: bash

   git clone https://github.com/SETI/rms-metadata-tools.git
   cd rms-metadata-tools
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"

The optional dependency groups are:

``dev``
    Linting, type-checking, test, and documentation tooling (``ruff``,
    ``mypy``, ``pytest``, ``pymarkdownlnt``, Sphinx, and others). Includes the
    ``docs`` group.
``docs``
    Sphinx and the extensions needed to build this documentation.
``cloud``
    ``rms-cloud-tasks`` and its dependencies, required only to run the
    distributed ``*_cloud.py`` workers (see :doc:`user_guide_cloud`).

Install a group with, for example, ``pip install -e ".[cloud]"``.

Environment variables
=====================

The programs do not read any environment variable directly. Instead, **every
path argument is expanded for environment variables** before use (``$NAME`` and
``${NAME}`` are both honored, and ``gs://`` / ``s3://`` URI prefixes are
preserved). This lets you keep the locations of your trees in the environment
and pass them symbolically on the command line.

The conventional variables used throughout this guide and in the host scripts'
examples are:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Variable
     - Meaning
   * - ``RMS_VOLUMES``
     - Root of the data volume tree (the PDS3 data products and their labels).
   * - ``RMS_METADATA``
     - Root of the metadata tree that holds the project-supplied corrected
       index files (the input to the index stage).
   * - ``RMS_METADATA_TEST``
     - Root of the output tree in which generated tables and labels are written.
       Point this at ``RMS_METADATA`` to write in place.

The test suite additionally reads ``RMS_METADATA`` and ``RMS_VOLUMES`` at
import time (see :doc:`/dev_guide/dev_guide_environment`). The check-runner
script honors ``VENV`` / ``VENV_PATH`` to locate the virtual environment.

You are free to use any variable names you like; these are only conventions.

Directory layout
================

The programs walk a *volume tree*: a collection directory (named for the PDS
volume set, e.g. ``GO_0xxx``) containing one subdirectory per volume (e.g.
``GO_0017``). A typical layout is:

.. code-block:: text

   $RMS_VOLUMES/
     GO_0xxx/                     # collection (volume set)
       GO_0017/                   # one volume
         <data products and PDS3 .LBL files, in subdirectories>
       GO_0018/
       ...

   $RMS_METADATA/
     GO_0xxx/
       GO_0017/
         GO_0017_index.tab        # project-supplied corrected index + label
         GO_0017_index.lbl
       ...

   $RMS_METADATA_TEST/            # output tree (may equal $RMS_METADATA)
     GO_0xxx/
       GO_0017/
         GO_0017_supplemental_index.tab   # written by the index stage
         GO_0017_supplemental_index.lbl
         GO_0017_sky_summary.tab          # written by the geometry stage
         GO_0017_body_summary.tab
         GO_0017_ring_summary.tab
         GO_0017_inventory.csv
         ...
       GO_0999/                           # cumulative output directory
         GO_0999_supplemental_index.tab   # written by the cumulative stage
         ...

A volume is recognized by matching its name against a glob derived from the
collection name (``GO_0xxx`` becomes ``GO_0[0-9][0-9][0-9]``). The cumulative
stage writes into a dedicated volume-like directory (``GO_0999`` for Galileo
SSI) that is excluded from the per-volume stages.

Running the programs
====================

The package does not install console scripts. Each collection has its own set
of runnable entry-point scripts in its host directory under
``src/metadata_tools/hosts/<HOST>/``. Because those scripts import their
configuration as top-level modules (``import host_config``,
``import index_config``, ``import geometry_config``), they resolve **only when
the current working directory is the host directory**. Always ``cd`` into the
host directory first:

.. code-block:: bash

   cd src/metadata_tools/hosts/GO_0xxx
   python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/"

A quick smoke test that generates one image's worth of metadata for a single
volume is shown in :doc:`user_guide_examples`.
