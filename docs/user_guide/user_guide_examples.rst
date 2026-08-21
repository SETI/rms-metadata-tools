========
Examples
========

The examples below use the Galileo SSI host (``GO_0xxx``) and the conventional
environment variables from :doc:`user_guide_installation`.

End-to-end run for one collection
=================================

The full three-stage pipeline for a collection, writing output under
``$RMS_METADATA_TEST``:

.. code-block:: bash

   export RMS_VOLUMES=/data/volumes
   export RMS_METADATA=/data/metadata
   export RMS_METADATA_TEST=/data/metadata_test

   # 1. Supplemental index tables for every volume.
   metadata-index GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/"

   # 2. Summary geometry tables for every volume.
   metadata-geometry GO_0xxx "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/"

   # 3. Cumulative tables across the whole collection.
   metadata-cumulative GO_0xxx "$RMS_METADATA_TEST/GO_0xxx/GO_0999/"

After stage 3 the output tree contains per-volume supplemental index, geometry,
and inventory tables (each with a ``.lbl`` label), plus the cumulative tables in
the ``GO_0999`` directory.

Quick smoke test
================

To verify your environment without processing a whole collection, restrict the
index and geometry stages to a single volume and a handful of files:

.. code-block:: bash

   metadata-index GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --volumes GO_0017
   metadata-geometry GO_0xxx "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/" \
       --volumes GO_0017 --first 5

The ``--first 5`` flag stops after five images, so the run completes in seconds
and writes a small set of tables you can inspect.

Generating only labels
======================

If the tables already exist and you only need to regenerate their labels (for
example after editing a template), pass ``--labels`` to any stage:

.. code-block:: bash

   metadata-geometry GO_0xxx "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/" \
       --volumes GO_0017 --labels

Using the engine from Python
============================

The console scripts are thin wrappers around the engine entry points. You can
call those functions directly from Python:

.. code-block:: python

   from metadata_tools.config import set_host
   from metadata_tools.index_support import process_index

   set_host('GO_0xxx')

   from metadata_tools.config import get_host_config, get_index_config
   hconf = get_host_config()
   iconfig = get_index_config()

   # Pass volumes explicitly; sys.argv supplies remaining options.
   process_index(hconf.template_name, glob=iconfig.glob, volumes=['GO_0017'])

The geometry and cumulative stages are driven the same way through
:func:`~metadata_tools.geometry_support.process.process_tables` and
:func:`~metadata_tools.cumulative_support.create_cumulative_indexes`.
