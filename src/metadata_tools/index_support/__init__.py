"""Tools for generating supplemental index tables and their PDS3 labels.

Re-exports the public API: IndexTable, the built-in key functions, and the
process entry points.
"""
from metadata_tools.index_support.key_fns import (
    key__file_specification_name,
    key__volume_id,
)
from metadata_tools.index_support.process import (
    get_args,
    process_index,
)
from metadata_tools.index_support.table import IndexTable

__all__ = [
    'IndexTable',
    'get_args',
    'key__file_specification_name',
    'key__volume_id',
    'process_index',
]
