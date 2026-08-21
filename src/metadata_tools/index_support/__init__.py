################################################################################
# index_support package - Tools for generating index files.
#
# Generates PDS3 supplemental index tables and their PDS3 labels. This module
# re-exports the public API: IndexTable, the built-in key functions, and the
# process entry points.
################################################################################
"""Tools for generating supplemental index tables and their PDS3 labels."""
from metadata_tools.index_support.key_fns import (
    key__file_specification_name,
    key__volume_id,
)
from metadata_tools.index_support.process import (
    _create_index,
    get_args,
    process_index,
)
from metadata_tools.index_support.table import IndexTable

__all__ = [
    'IndexTable',
    '_create_index',
    'get_args',
    'key__file_specification_name',
    'key__volume_id',
    'process_index',
]
