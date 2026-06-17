========
Examples
========

The examples below use the Galileo SSI host (``GO_0xxx``) and the conventional
environment variables from :doc:`user_guide_installation`. Every example is run
from inside the host directory.

End-to-end run for one collection
=================================

The full three-stage pipeline for a collection, writing output under
``$RMS_METADATA_TEST``:

.. code-block:: bash

   export RMS_VOLUMES=/data/volumes
   export RMS_METADATA=/data/metadata
   export RMS_METADATA_TEST=/data/metadata_test

   cd src/metadata_tools/hosts/GO_0xxx

   # 1. Supplemental index tables for every volume.
   python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/"

   # 2. Summary geometry tables for every volume.
   python GO_0xxx_geometry.py "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/"

   # 3. Cumulative tables across the whole collection.
   python GO_0xxx_cumulative.py "$RMS_METADATA_TEST/GO_0xxx/GO_0999/"

After stage 3 the output tree contains per-volume supplemental index, geometry,
and inventory tables (each with a ``.lbl`` label), plus the cumulative tables in
the ``GO_0999`` directory.

Quick smoke test
================

To verify your environment without processing a whole collection, restrict the
index and geometry stages to a single volume and a handful of files:

.. code-block:: bash

   cd src/metadata_tools/hosts/GO_0xxx
   python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" -vv GO_0017
   python GO_0xxx_geometry.py "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/" \
       -vv GO_0017 --first 5

The ``--first 5`` flag stops after five images, so the run completes in seconds
and writes a small set of tables you can inspect.

Generating only labels
======================

If the tables already exist and you only need to regenerate their labels (for
example after editing a template), pass ``--labels`` to any stage:

.. code-block:: bash

   python GO_0xxx_geometry.py "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/" \
       -vv GO_0017 --labels

Using the engine from Python
============================

The host programs are thin wrappers around the engine entry points. You can call
those functions directly, but the same host-directory rule applies: the host
configuration modules must be importable, so run from inside the host directory
(or place it on ``sys.path``). The functions parse the command line themselves
unless you pass an ``args`` namespace.

.. code-block:: python

   # Run from inside src/metadata_tools/hosts/GO_0xxx so that host_config,
   # index_config, and geometry_config resolve as top-level modules.
   import host_config as hconf
   import index_config as iconfig

   from metadata_tools.index_support import process_index

   # sys.argv supplies volume_tree, metadata_tree, output_tree and any options.
   process_index(hconf.template_name, glob=iconfig.glob, volumes=["GO_0017"])

The geometry and cumulative stages are driven the same way through
:func:`~metadata_tools.geometry_support.process.process_tables` and
:func:`~metadata_tools.cumulative_support.create_cumulative_indexes`.
