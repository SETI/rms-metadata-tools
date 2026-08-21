=========================
Appendix: Supported hosts
=========================

A *host* is a supported collection. Each host has its own directory under
``src/metadata_tools/hosts/<HOST>/`` containing its configuration and label
templates. The ten console scripts (``metadata-index``, ``metadata-geometry``,
``metadata-cumulative``, their ``*-worker`` and ``*-cloud`` counterparts, and
``metadata-task-list``) work with any installed host; pass the host ID as the
first positional argument.

The programs and options documented in this guide are the same for every host;
only the host ID and its specific defaults change. To add support for a new
collection, see :doc:`/dev_guide/dev_guide_extending`.

Galileo SSI (``GO_0xxx``)
=========================

The Galileo Solid-State Imaging (SSI) host.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Host directory
     - ``src/metadata_tools/hosts/GO_0xxx``
   * - NAIF spacecraft ID
     - ``-77``
   * - Data label glob
     - ``C0*.LBL``
   * - Default geometry selection
     - ``"S"`` (summary tables)
   * - Cumulative directory
     - ``GO_0xxx/GO_0999`` (excluded from the per-volume stages)
   * - ``oops`` host module
     - ``oops.hosts.galileo.ssi``

The host's mission table maps spacecraft-clock ranges to the primary body and
the bodies of interest for the Venus, Earth, SL9, and Jupiter phases of the
mission. Calibration and similar observations are excluded by the host's
exception patterns. These details live in the host's ``geometry_config.py`` and
are described, as an extension example, in
:doc:`/dev_guide/dev_guide_extending`.
