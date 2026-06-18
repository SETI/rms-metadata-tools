#!/usr/bin/env python
"""Generate cumulative tables and labels for Galileo SSI.

Concatenates the per-volume tables across the whole volume tree. Run this script from
inside its host directory (hosts/GO_0xxx), because it does top-level
``import host_config`` which only resolves when the host directory is on sys.path.

Examples:
    python3 GO_0xxx_cumulative.py $RMS_METADATA_TEST/GO_0xxx/GO_0999/
    python3 GO_0xxx_cumulative.py $RMS_METADATA/GO_0xxx/GO_0999/ -vv GO_0017

The full list of command-line options is documented in the user guide.
"""
import host_init  # noqa: F401  (imported for side effects)

import metadata_tools.cumulative_support as cml

cml.create_cumulative_indexes('GO_0xxx_supplemental_index',
                              exclude=['GO_0999'])
##########################################################################################
