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
    spacecraft-clock formatting constants, and ``get_volume_id()``, which
    extracts the volume ID from a path.

``index_config.py``
    Index-stage settings: ``glob`` (which data labels to include, e.g.
    ``C0*.LBL``) and any ``key__<NAME>`` functions that compute an index column
    from the PDS3 label instead of copying it verbatim.

``geometry_config.py``
    Geometry-stage settings, including:

    - ``SC`` — the NAIF spacecraft ID.
    - ``glob`` / ``index_glob`` — patterns selecting data labels and the
      supplemental index file.
    - ``selection`` — default table levels (``"S"`` summary, ``"D"`` detailed).
    - ``exclude`` — volumes to skip (e.g. the cumulative directory).
    - ``MISSION_TABLE`` and ``EXCEPTIONS`` — the mapping from spacecraft-clock
      ranges to the primary body, secondaries, and other selected bodies, with
      regular-expression or predicate exceptions.
    - The field-of-view expansion constants and the ``meshgrids`` /
      ``meshgrid`` functions that define pixel sampling.
    - ``from_index``, ``target_name``, and ``cleanup`` hooks.

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
- Geometry detailed: ``<volume>_<kind>_detailed.tab``.
- Cumulative: the same names with the cumulative directory's volume ID.

Each ``.tab``/``.csv`` file is accompanied by a ``.lbl`` PDS3 label generated
from the host's label template (or a shared template in the package's global
``templates/`` directory). The set of columns in an index table is itself
defined by the supplemental label template; see
:doc:`/dev_guide/dev_guide_extending`.
