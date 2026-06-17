====================
Extending the system
====================

There are three extension points: adding a whole new host (collection), adding
an index column via a key function, and adding a geometry column. Each is
described below with a minimal skeleton.

Adding a new host
=================

A host is a package under ``src/metadata_tools/hosts/<HOST>/``. The fastest path
is to copy the Galileo SSI host and adapt it:

#. Create ``src/metadata_tools/hosts/<HOST>/`` (named for the PDS volume set,
   e.g. ``COISS_xxxx``).
#. Copy the Python modules and the ``<HOST>_*`` scripts from an existing host and
   rename the scripts for the new collection.
#. Edit the configuration modules (below) and ``host_init.py``.
#. Create a ``templates/`` subdirectory, copy the templates, rename them, edit
   ``host_defs.lbl`` and the summary templates, and define the supplemental
   metadata in the supplemental template.

The configuration modules form the contract the engine relies on. The host
scripts import them as the top-level names ``host_config``, ``index_config``, and
``geometry_config``, so they only resolve when the current working directory is
the host directory.

``host_config.py`` must provide:

.. code-block:: python

   template_name = '<HOST>_supplemental_index'   # base name of templates/tables

   def get_volume_id(label_path):
       """Return the volume ID for a path under this collection."""
       ...

``index_config.py`` must provide the data-label ``glob`` and may provide any
number of ``key__<name>`` column functions:

.. code-block:: python

   glob = 'C0*.LBL'   # which data labels to include

   def key__start_time(label_path, label_dict):
       """Compute the START_TIME column for one data product."""
       ...

``geometry_config.py`` must provide the spacecraft ID, file globs, default
selection and exclusions, the body-selection ``MISSION_TABLE`` (and its
``EXCEPTIONS``), the ``from_index`` reader, the ``meshgrids`` / ``meshgrid``
functions, ``target_name``, and ``cleanup``:

.. code-block:: python

   import oops.hosts.<mission>.<instrument> as inst

   SC = -77                       # NAIF spacecraft ID
   glob = 'C0*.LBL'
   index_glob = '<HOST>_????_index.lbl'
   selection = 'S'
   exclude = ['<HOST>_9999']
   MISSION_TABLE = [ ... ]        # SCLK ranges -> primary, secondaries, ...
   EXCEPTIONS = [ ... ]           # regexes/predicates excluded from the SCLK test
   from_index = inst.from_index

   def meshgrids(sampling): ...
   def meshgrid(meshgrids, snapshot): ...
   def target_name(snapshot): ...
   def cleanup(): ...

``host_init.py`` initializes the ``oops`` host module so the body registry is
populated, and is imported only for that side effect:

.. code-block:: python

   import oops.hosts.<mission>.<instrument> as inst
   inst.initialize()

Finally, add tests under ``tests/hosts/<HOST>/`` (marked ``requires_archive``).

Adding an index column (key function)
=====================================

By default each column in the supplemental label template names a PDS3 label
field to copy verbatim. To compute a column instead, add a key function to the
host's ``index_config.py``:

.. code-block:: python

   def key__<column_name_lowercase>(label_path, label_dict):
       """Return the value to write under <COLUMN_NAME>, or None for null."""
       ...

The function receives the label path and the parsed label dictionary and returns
the value (return ``None`` to write the column's null constant). Add the matching
column object to the supplemental template so the column exists in the output.
The resolution order (built-in key function, then host key function, then the raw
label field) is described in :doc:`dev_guide_index_subsystem`.

Adding a geometry column
========================

Adding a geometry column touches the column definition, the backplane, the
format dictionary, the label template, and the tests:

#. Add a column-description tuple to the relevant module in the
   :mod:`metadata_tools.columns` package (``body``, ``ring``, ``sky``, or
   ``sun``). The tuple is ``(backplane_key, (masker, shadower, face))`` with an
   optional alternate-format tag (see :doc:`dev_guide_geometry_subsystem`).
#. Add the corresponding backplane function in ``oops`` if the backplane key is
   new.
#. Add a row for the column to
   :data:`~metadata_tools.geometry_support.formats.FORMAT_DICT` (the ten-element
   format tuple described in :ref:`format-dict-contract`).
#. Add the column description(s) to the host's summary (or detailed) label
   template, e.g. ``GO_0xxx_body_summary.lbl``.
#. Run the host's geometry program and update the unit tests.
