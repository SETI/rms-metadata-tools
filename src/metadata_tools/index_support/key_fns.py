################################################################################
# key_fns.py - Built-in key functions for index table columns.
################################################################################
"""Built-in key functions for index table columns."""
from pathlib import Path
from typing import Any, cast

from filecache import FCPath

import metadata_tools.util as util
from metadata_tools.config import get_host_config


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
    return cast(str, get_host_config().get_volume_id(label_path))

#===============================================================================
def key__file_specification_name(label_path: str | Path | FCPath,
                                 label_dict: dict[str, Any]) -> FCPath:
    """Key function for FILE_SPECIFICATION_NAME.  The return value will appear in
    the index file under FILE_SPECIFICATION_NAME.

    Parameters:
        label_path: Path to the PDS label.
        label_dict: Dictionary containing the PDS label fields.

    Returns:
        File Specification name.
    """
    label_path = FCPath(label_path)
    return util.get_volume_subdir(label_path, get_host_config().get_volume_id(label_path))
