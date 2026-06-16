#!/usr/bin/env python
"""Generate all geometry tables and labels for Galileo SSI.

Run this script from inside its host directory (hosts/GO_0xxx), because it does
top-level ``import host_config`` / ``import geometry_config`` which only resolve when
the host directory is on sys.path.

Example:
    python3 GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/

The full list of command-line options is documented in the user guide.
"""
import geometry_config as config
import host_init  # noqa: F401  (imported for side effects)

import metadata_tools.geometry_support as geom

geom.process_tables('GO_0xxx_supplemental_index',
                    glob=config.glob,
                    index_glob=config.index_glob,
                    selection="S",
                    exclude=['GO_0999'])
##########################################################################################
