=================
Repository layout
=================

The importable public package is everything under ``src/metadata_tools/``
*except* the ``hosts/`` subpackage. The ``hosts/`` subpackage and everything
outside ``src/`` is supporting code: per-collection configuration, runnable
scripts, tests, docs, and tooling.

.. code-block:: text

   rms-metadata-tools/
     pyproject.toml            # packaging, dependencies, and tool configuration
     requirements.txt          # runtime requirements (mirrors pyproject)
     README.md                 # project front page (included into these docs)
     CONTRIBUTING.md           # contribution workflow
     codecov.yml               # coverage service configuration
     scripts/
       run-all-checks.sh       # single source of truth for the quality gates
       read-docs.sh            # build the docs (-W) and open them in a browser
     docs/                     # Sphinx documentation source (this site)
       conf.py                 # single Sphinx configuration
       index.rst               # documentation root
       user_guide/             # the end-user manual
       dev_guide/              # this developer manual, including api/
     tests/                    # pytest suite (see Environment setup)
       hosts/<HOST>/           # host-specific tests (requires_archive)
     src/
       metadata_tools/         # the importable engine (public package)
         __init__.py           # package docstring and version
         common.py             # Table base class, global logger, task plumbing
         index_support.py      # IndexTable and process_index()
         geometry_support/     # geometry engine (package)
         cumulative_support.py # cumulative table concatenation
         label_support.py      # PDS3 label generation from templates
         columns/              # geometry column definitions (body/ring/sky/sun)
         bodies.py             # builds the oops Body registry
         util.py               # path, text, time, and math utilities
         defs.py               # constants (body names, ring radii, paths)
         templates/            # shared PDS3 label-template fragments
         hosts/                # per-collection configuration + scripts
           GO_0xxx/            # Galileo SSI host (the reference example)

The geometry engine is a package:

.. code-block:: text

   src/metadata_tools/geometry_support/
     __init__.py        # re-exports the public surface (entry points + classes)
     process.py         # get_args() and process_tables() (the stage entry point)
     suite.py           # Suite: the set of geometry tables for one volume
     record.py          # Record: one observation's row across all tables
     tables.py          # InventoryTable, SkyTable, SunTable, RingTable, BodyTable
     prep.py            # prep_row(): builds the formatted columns for a row
     masks.py           # construct_excluded_mask(): excluded-pixel masks
     formatting.py      # numeric/ISO column formatting
     formats.py         # FORMAT_DICT: per-column format/units/null/range metadata
     bodies_select.py   # primary/body selection and field-of-view inventory

A host directory mixes configuration, templates, and runnable scripts:

.. code-block:: text

   src/metadata_tools/hosts/GO_0xxx/
     host_config.py            # shared host settings + get_volume_id()
     index_config.py           # index glob + key__<NAME> column functions
     geometry_config.py        # SPICE id, mission table, meshgrids, hooks
     host_init.py              # initializes the oops host module (side effects)
     GO_0xxx_index.py          # local index entry point (argparse CLI)
     GO_0xxx_geometry.py       # local geometry entry point
     GO_0xxx_cumulative.py     # local cumulative entry point
     GO_0xxx_*_cloud.py        # rms-cloud-tasks (GCP) counterparts
     gcp_*_config.yml          # GCP machine/queue configuration
     gcp_*_startup.sh          # GCP instance start-up scripts
     templates/                # host PDS3 label templates
