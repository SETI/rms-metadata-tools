################################################################################
# key_fns.py - Built-in key functions for index table columns.
################################################################################
"""Built-in key functions for index table columns."""
from pathlib import Path
from typing import Any

from filecache import FCPath

import metadata_tools.config as hooks
import metadata_tools.util as util


#===============================================================================
def key__volume_id(label_path: str | Path | FCPath,
                   label_dict: dict[str, Any]) -> str:
    """Key function for VOLUME_ID. The return value will appear in the index
    file under VOLUME_ID.

    Parameters:
        label_path: Path to the PDS label.
        label_dict: Dictionary containing the PDS label fields.

    Returns:
        Volume ID.
    """
    return hooks.get_volume_id(FCPath(label_path))

#===============================================================================
def key__file_specification_name(label_path: str | Path | FCPath,
                                 label_dict: dict[str, Any]) -> FCPath:
    """Key function for FILE_SPECIFICATION_NAME. The return value will appear in
    the index file under FILE_SPECIFICATION_NAME.

    Parameters:
        label_path: Path to the PDS label.
        label_dict: Dictionary containing the PDS label fields.

    Returns:
        File Specification name.
    """
    label_path = FCPath(label_path)
    return util.get_volume_subdir(label_path, hooks.get_volume_id(label_path))
