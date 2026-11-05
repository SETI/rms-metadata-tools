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
   * - Cumulative directory
     - ``GO_0xxx/GO_0999`` (excluded from the per-volume stages)
   * - ``oops`` host package
     - ``rms-host-galileo``: ``host_galileo.oops`` (class ``GalileoSSI``)

The host's mission table maps spacecraft-clock ranges to the primary body and
the bodies of interest for the Venus, Earth, SL9, and Jupiter phases of the
mission. Calibration and similar observations are excluded by the host's
exception patterns. These details live in the host's ``geometry_config.py`` and
are described, as an extension example, in
:doc:`/dev_guide/dev_guide_extending`.

Cassini ISS (``COISS_xxxx``)
============================

The Cassini Imaging Science Subsystem (ISS) host. One host serves both
collections, ``COISS_1xxx`` (cruise and the Jupiter flyby) and ``COISS_2xxx``
(Saturn), and both cameras: the narrow-angle and wide-angle images of a volume
share its tables.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Host directory
     - ``src/metadata_tools/hosts/COISS_xxxx``
   * - NAIF spacecraft ID
     - ``-82``
   * - Data label glob
     - ``[NW]*.LBL``
   * - Cumulative directories
     - ``COISS_1xxx/COISS_1999`` and ``COISS_2xxx/COISS_2999`` (excluded from
       the per-volume stages)
   * - ``oops`` host package
     - ``rms-host-cassini``: ``host_cassini.oops`` (class ``CassiniISS``)

The host's mission table covers the Earth flyby, the Jupiter flyby, and the
Saturn approach and tour. The index on each Cassini ISS volume already holds
the values a supplemental index would add, so the host defines no supplemental
index template and the geometry stage reads the volume's index alone.

Since there is no index stage, nothing creates the volume directories of the
output tree, as the index stage does for other hosts. Each volume to process
needs a directory there before the geometry stage runs; on Google Cloud Storage,
where a directory exists only through the files in it, it must hold at least one
file, such as a copy of the volume's index. A volume named by ``--volumes`` that
has no directory there is an error. ``cloud/COISS_xxxx/`` has GCP configs for
the geometry and cumulative stages only.

Voyager ISS (``VGISS_xxxx``)
============================

The Voyager Imaging Science Subsystem (ISS) host. One host serves all four
collections, ``VGISS_5xxx`` (Jupiter), ``VGISS_6xxx`` (Saturn), ``VGISS_7xxx``
(Uranus), and ``VGISS_8xxx`` (Neptune), both spacecraft, and both cameras. In a
volume ID ``VGISS_<P><S><NN>``, the digit ``S`` names the spacecraft (``1`` or
``2``; ``9`` for the cumulative volume).

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Host directory
     - ``src/metadata_tools/hosts/VGISS_xxxx``
   * - NAIF spacecraft ID
     - None: the mission table is keyed by time (the spacecraft are ``-31`` and
       ``-32``)
   * - Data label glob
     - ``C*_RAW.LBL``
   * - Index read by the geometry stage
     - ``VGISS_*_raw_image_index.lbl``, with the volume's supplemental index
   * - Cumulative directories
     - ``VGISS_5999``, ``VGISS_6999``, ``VGISS_7999``, and ``VGISS_8999`` under
       their collections (excluded from the per-volume stages)
   * - ``oops`` host package
     - ``rms-host-voyager``: ``host_voyager.oops`` (class ``VoyagerISS``); not
       yet published

Each collection holds the images of both spacecraft, whose clocks cannot be
compared, so the host's mission table is keyed by time: one row for each
planet, spanning both spacecraft's encounters there. Calibration frames (the
targets ``DARK``, ``CAL LAMPS``, and ``PLAQUE``) are excluded by a predicate,
since the Voyager index has no ``OBSERVATION_ID``.

Each image is archived as several products; the geometry describes the raw
image, and reads the volume's raw-image index, which has one row per image,
rather than its full index, which has one per product. The RMS Node's metadata
already holds each volume's supplemental index, so, as for Cassini ISS, there
is no index stage, and each volume to process needs a directory in the output
tree before the geometry stage runs.
