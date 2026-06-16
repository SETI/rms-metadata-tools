################################################################################
# Shared helpers for the $RMS_METADATA archive-backed tests
################################################################################
import glob
import os
from typing import Any

import numpy as np

# Read lazily so that importing this support module never fails at collection
# time when the holdings tree is absent. The tests that actually use these are
# marked ``requires_archive`` and excluded from the default run.
METADATA = os.environ.get('RMS_METADATA')
VOLUMES = os.environ.get('RMS_VOLUMES')

#===============================================================================
# get summary filenames  ### LIB
def match(tree: str, pattern: str) -> list[str]:
    """Walk a directory tree and find all files matching a given pattern.

    Args:
        tree (str): Directory to walk.
        pattern (str): glob pattern to match.

    Returns:
        list: List of filenames matching the given pattern.
    """
    all_files: list[str] = []
    for root, _dirs, _files in os.walk(tree):
        all_files += glob.glob(os.path.join(root, pattern))
    return all_files

#===============================================================================
# exclude test files  ### LIB
def exclude(files: list[str], *patterns: str) -> list[str]:
    """Exclude files matching given patterns.

    Args:
        files (list): List of file names to test.
        patterns (str): One or more strings containing forbidden patterns.

    Returns:
        list: List of filenames that did not match any of the given patterns.
    """
    result: list[str] = []
    for i in range(len(files)):
        keep = True
        for pattern in patterns:
            if files[i].find(pattern) != -1:
                keep = False
        if keep:
            result += [files[i]]
    return result

#===========================================================================
def bounds(file: str, table: Any, key: str,
           min_val: float = 0, max_val: float = 360, minmax: bool = True) -> None:
    """Test whether values exeed given minimum and maximum bounds.

    Args:
        file (str): Name of data file.
        table (pdsTable): PdsTable object containing the data table.
        key (tstr):
            Name of quantity to test.  If minmax==True, the "MINIMUM_" and
            "MAXIMUM_" prefixes must be omitted, and the function will add them
            and test both keys.
        min_val (float): Minimum allowable value.
        max_val (float): Maximum allowable value.
        minmax (bool): If set, both the  are "MINIMUM_" and "MAXIMUM_" keys are
                       tested.  In this case, those prefixes must be omitted
                       from the key argument.

    Returns:
        None.
    """
    if minmax:
        bounds(file, table, 'MINIMUM_' + key, minmax=False, min_val=min_val, max_val=max_val)
        bounds(file, table, 'MAXIMUM_' + key, minmax=False, min_val=min_val, max_val=max_val)
        return

    nullvals = table.info.column_info_dict[key].invalid_values.copy()
    nullval = None
    if nullvals:
        nullval = nullvals.pop()

    val = table.column_values[key]

    assert not np.any(np.where(np.logical_and(np.logical_or(val < min_val, val > max_val),
                                              val != nullval))), (key, file)
################################################################################
