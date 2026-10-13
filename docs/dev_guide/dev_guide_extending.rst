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
   e.g. ``COISS_xxxx``). Copy ``host_config.py``, ``index_config.py``,
   ``geometry_config.py``, ``host_init.py``, and ``__init__.py`` from an existing
   host (e.g. ``GO_0xxx``) as a starting point.
#. Edit the configuration modules (below) and ``host_init.py``.
#. Create a ``templates/`` subdirectory holding two templates: ``host_defs.lbl``
   and ``<HOST>_supplemental_index.lbl``. Copy them from an existing host, edit
   ``host_defs.lbl`` (below), and define the supplemental metadata in the
   supplemental template. The summary and inventory tables are labeled from the
   templates all hosts share.

``host_defs.lbl`` states the mission and instrument keywords that appear in
every label, and defines the values the shared summary templates
(``<kind>_summary.lbl`` in ``src/metadata_tools/templates/``) take from the
host:

.. code-block:: text

   # The instrument, as it reads in a sentence
   $ONCE(instrument = 'Galileo SSI')
   # What one data product is called, and its plural: image, spectrum, ...
   $ONCE(product = 'image')
   $ONCE(products = 'images')
   # Widths of a volume ID and of the FILE_SPECIFICATION_NAME column
   $ONCE(volume_id_bytes = 7)
   $ONCE(filespec_bytes = 32)
   $ONCE(system_names = 'EARTH, VENUS, or JUPITER')
   $ONCE(ring_system = 'Jupiter')
   $ONCE(is_visual = True)
   $ONCE(is_saturn = False)

The templates take three more values from the engine, not from
``host_defs.lbl``: ``FOV_BORDER``, the host's ``host_config.BORDER`` worded as
an angle (the border sentence is omitted for a host with no border), and ``SAMPLING``
and ``BODY_SAMPLES``, the sampling a geometry
table was generated with. The last two are known only to a geometry run, so a
cumulative label describes the sampling without stating its values.

Each ``$ONCE`` value must be a literal: the geometry stage reads the column widths from the
templates without generating a label, and substitutes only literal definitions
(:func:`~metadata_tools.column_grammar.substitute_constants`). The values land
in fixed lines of label prose, so keep them short enough that no line of a
generated label outgrows the PDS3 line length.

A host that must differ from a shared template -- a summary table or the
inventory -- places a copy of its own, named ``<HOST>_<kind>.lbl``, in its
``templates/`` directory; :func:`~metadata_tools.util.find_template` prefers it.

The configuration modules form the contract the engine relies on. Console-script
entry points call :func:`metadata_tools.config.set_host` with the host id, which
package-imports ``metadata_tools.hosts.<HOST>.host_config`` and ``index_config``
(``geometry_config`` is imported lazily on first use); the engine then reads them
through :func:`~metadata_tools.config.get_host_config`,
:func:`~metadata_tools.config.get_index_config`, and
:func:`~metadata_tools.config.get_geometry_config`. No current-working-directory
convention is involved.

``host_config.py`` must provide:

.. code-block:: python

   template_name = '<HOST>_supplemental_index'   # base name of templates/tables
   glob = 'C0*.LBL'               # which data labels to include

and may override two engine defaults:

.. code-block:: python

   exclude = ['<HOST>_0001']      # volumes excluded from processing; by default
                                   # the cumulative volume of the tree being
                                   # processed (GO_0999 under GO_0xxx)

   def get_volume_id(label_path):
       """Return the volume ID for a path under this collection.

       By default the volume is the directory under the collection directory,
       e.g. COISS_2001 under COISS_2xxx (util.get_volume_id).
       """
       ...

``index_config.py`` may provide any number of ``key__<name>`` column functions:

.. code-block:: python

   def key__start_time(label_path, label_dict):
       """Compute the START_TIME column for one data product."""
       ...

``geometry_config.py`` must provide the spacecraft ID, default selection, the
body-selection ``MISSION_TABLE`` (and its ``EXCEPTIONS``), and the
``from_index`` reader:

.. code-block:: python

   import oops.hosts.<mission>.<instrument> as inst

   SC = -77                       # NAIF spacecraft ID
   selection = 'S'
   MISSION_TABLE = [ ... ]        # SCLK ranges -> primary, secondaries, ...
   EXCEPTIONS = [ ... ]           # regexes/predicates excluded from the SCLK test
   from_index = inst.from_index

The border to allow around a field of view is not set here but in
``host_config.py``, since the labels state it too. It reflects the uncertainty
in the spacecraft pointing, so it is an angle, the same for every instrument of
the spacecraft:

.. code-block:: python

   BORDER = 1.5e-4     # radians

With no ``BORDER``, the field of view is sampled as it is. The engine samples
each observation's own FOV (``observation.fov``) with that border around it, and
takes the inventory of bodies in view with the same allowance. Because the
border is an angle, a summed mode or a wider camera gets proportionally fewer
pixels of it, and the labels state it as an angle alone.

It may also override these engine defaults, read through the accessors in
:mod:`metadata_tools.config`:

.. code-block:: python

   EXTRA_CHILDREN = ['PHOEBE']            # default: regular children only
   index_glob = '<HOST>_????_index.lbl'   # default: <volume_id>_index.lbl
   def target_name(snapshot): ...         # default: snapshot['TARGET_NAME']
   def cleanup(): ...                     # default: nothing to clean up
   def meshgrids(sampling): ...           # default: an empty cache, and
   def meshgrid(meshgrids, snapshot): ... #   a meshgrid of snapshot.fov

The engine considers only the regular children of a planet, since the irregular
moons of the giant planets are numerous and their number keeps growing.
``EXTRA_CHILDREN`` names the irregular moons a host wants treated exactly as
the regular ones are: reachable by the mission table's selections, listed in the
inventory, and ordered with their siblings. Each must be a child of one of the
engine's planets, or the registry refuses it.

The width of the FILE_SPECIFICATION_NAME column is whatever the host's summary
templates declare for it (they must agree); the engine pads the file
specification to that width in every table, and the inventory label reports the
widths found in the table.

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

The label templates define a geometry column end to end -- its label metadata
and its computation -- so a new column is a template edit plus, at most, a new
backplane function. The geometry column set is the same for every collection:
it lives in the shared fragments in ``src/metadata_tools/templates/``
(``body_summary_columns.lbl``, ``ring_summary_columns.lbl``, and so on), which
the shared summary templates pull in with ``$INCLUDE``. A summary template
itself, ``<kind>_summary.lbl``, carries only the prefix columns and the
table-level boilerplate.

#. For a two-valued column, add a ``COLUMN_DEFINITION`` object to the shared
   fragment for its table kind, naming the quantity and declaring what its
   values share: ``FORMAT``,
   ``UNIT`` (which drives the unit conversion), ``NULL_CONSTANT``, the valid
   range -- or, when the column shares one of the common formats,
   ``COLUMN_FORMAT`` naming its entry in the format dictionary
   (``column_formats.lbl``) in place of those keywords -- the shared lead-in
   ``DESCRIPTION`` (what the quantity *is*), and the computation --
   ``BACKPLANE_KEY`` (a Python tuple literal, with ``'bodyx'`` where the body
   name goes), ``MASK`` if any bodies mask it, ``OVERFLOW_FORMAT`` (in PDS3
   FORMAT notation) if a value can outgrow its field, ``MESHGRID_MARGIN`` if
   the quantity reaches beyond the body's bounding box, and ``LINK_ID`` if a
   postprocessing rule ties the column to others. A ``LINK_ID`` names its link
   function: ``X`` calls ``link__x()``, which must exist in
   ``geometry_support/link_fns.py`` or the host's ``geometry_config``
   (``CENTER_COORDINATE``, the one group so far, nulls the whole group
   when any member is null).
#. Follow it with one ``COLUMN_STUB`` object per value -- minimum then
   maximum -- each declaring
   its ``NAME``, its own ``DESCRIPTION`` (what *this value* tabulates, which
   the write path appends to the definition's lead-in), and any keyword it
   overrides. A single-valued column needs neither definition nor stub: write
   it as a plain ``COLUMN`` carrying its own spec keywords alongside its
   label keywords. See :doc:`dev_guide_geometry_subsystem` for the full
   grammar; the write path lowers every group to plain ``COLUMN`` objects and
   removes the spec keywords, so none of this reaches the archive.
#. If the new column's format recurs among other columns but has no entry
   yet, consider adding one to ``column_formats.lbl`` and referring the
   columns to it; a one-off format stays inline.
#. Add the corresponding backplane function in ``oops`` if the quantity is new.
#. Regenerate a volume and update the unit tests -- the shipped templates'
   column counts are pinned in ``tests/test_geometry_schema.py``.

Removing a column is likewise a template-only edit: delete the definition and
its stubs (or the single ``COLUMN``), and the computation goes with them.

In the rare case that one collection must genuinely differ, a host can place
its own edited copy of a fragment in its ``templates/`` directory: the host's
directory is searched first when ``$INCLUDE`` resolves
(:class:`~metadata_tools.label_support.HostTemplate`), so the host copy shadows
the shared one for that host alone.
