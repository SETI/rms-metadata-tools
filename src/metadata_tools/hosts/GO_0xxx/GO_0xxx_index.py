#!/usr/bin/env python
"""Generate supplemental index tables and labels for Galileo SSI.

Run this script from inside its host directory (hosts/GO_0xxx), because it does
top-level ``import host_config`` / ``import index_config`` which only resolve when the
host directory is on sys.path.

Examples:
    python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
    python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -vv GO_0017

The full list of command-line options is documented in the user guide.
"""
import host_init  # noqa: F401  (imported for side effects)
import index_config as config

import metadata_tools.index_support as idx

idx.process_index('GO_0xxx_supplemental_index',
                  glob=config.glob)
##########################################################################################
