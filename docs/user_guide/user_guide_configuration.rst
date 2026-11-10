=============
Configuration
=============

A run is configured from three sources. When more than one supplies the same
setting, the earlier one wins:

1. **Command-line flags** passed to a host program (highest priority).
2. **Host configuration defaults** that the host entry script passes to the
   engine. These come from the host's configuration files and become the
   argparse defaults, so any command-line flag overrides them.
3. **Built-in engine defaults** (lowest priority), such as a pixel sampling
   density of 8.

This chapter describes the configuration a host supplies. The command-line
flags are documented per program in :doc:`user_guide_index`,
:doc:`user_guide_geometry`, and :doc:`user_guide_cumulative`. Authoring a new
host's configuration is covered in :doc:`/dev_guide/dev_guide_extending`.

Host configuration files
========================

Each collection lives in a host directory under
``src/metadata_tools/hosts/<HOST>/`` and carries a small set of configuration
modules. When you run an existing host you do not edit these, but it helps to
know what they control.

``host_config.py``
    Settings shared by every stage: ``template_name`` (the base name of the
    host's label templates and tables, e.g. ``GO_0xxx_supplemental_index``),
    ``glob`` (which data labels to include, e.g. ``C0*.LBL``), and
    ``BORDER`` (the border allowed around every field of view for uncertainty
    in the spacecraft pointing, in radians; the engine expands each field of
    view by it and the labels state it), and
    spacecraft-clock formatting constants. Two settings are optional, each
    with an engine default: ``exclude`` (volumes to skip; by default the
    cumulative volume of the tree being processed) and ``get_volume_id()``
    (by default the volume ID is read from the path, as the directory under
    the collection directory).

``index_config.py``
    Any ``key__<NAME>`` functions that compute an index column from the PDS3
    label instead of copying it verbatim.

``geometry_config.py``
    Geometry-stage settings, including:

    - ``SC`` — the NAIF spacecraft ID.
    - ``MISSION_TABLE`` and ``EXCEPTIONS`` — the mapping from spacecraft-clock
      ranges to the primary body, secondaries, and other selected bodies, with
      regular-expression or predicate exceptions.
    - The ``from_index`` hook.
    - Optionally, ``EXTRA_CHILDREN`` — irregular moons to treat exactly as the
      regular children of their planets are, in the selection of bodies and in
      the inventory. By default only regular children are considered.
    - Optionally, ``index_glob`` (by default a volume's index label is
      ``<volume_id>_index.lbl``), ``target_name`` (by default the
      observation's TARGET_NAME), ``cleanup`` (by default nothing), and
      ``meshgrids`` / ``meshgrid`` (to replace the default pixel sampling).

``host_init.py``
    Imported for its side effects: it initializes the ``oops`` host module
    (loading the SPICE data) so the geometry stage can compute backplanes.

How table and label names are formed
====================================

Output names are derived from the volume ID and the table kind, so you do not
configure them directly:

- Index: ``<volume>_supplemental_index.tab`` / ``.lbl``.
- Geometry summary: ``<volume>_<kind>_summary.tab`` for ``sky``, ``body``, and
  ``ring``; the inventory is ``<volume>_inventory.csv``.
- Cumulative: the same names with the cumulative directory's volume ID.

Each ``.tab``/``.csv`` file is accompanied by a ``.lbl`` PDS3 label generated
from the host's label template (or a shared template in the package's global
``templates/`` directory).

The label templates also define the columns themselves, for geometry tables as
well as index tables. The geometry column set is the same for every collection
and lives in shared template fragments that the shared summary templates
(``<kind>_summary.lbl``) pull in: a single-valued column is one
``COLUMN`` object, and a min/max pair is one ``COLUMN_DEFINITION`` object
followed by a ``COLUMN_STUB`` per value, with each column's null value, valid
range, and field width coming from its own object or from the definition it
shares. To add or drop a column, edit the shared fragment; see
:doc:`/dev_guide/dev_guide_extending`.
