################################################################################
# Global metadata unit test functions
################################################################################
import glob
import os
import numpy as np

METADATA = os.environ['RMS_METADATA']
VOLUMES = os.environ['RMS_VOLUMES']

#===============================================================================
# get summary filenames  ### LIB
def match(dir, pattern):
    """Walk a directory tree and find all files matching a given pattern.

    Args:
        dir (str): Directory to walk.
        pattern (str): glob pattern to match.

    Returns:
        list: List of filenames matching the given pattern.
    """
    all_files = []
    for root, dirs, files in os.walk(dir):
        all_files += glob.glob(os.path.join(root, pattern))
    return all_files

#===============================================================================
# exclude test files  ### LIB
def exclude(files, *patterns):
    """Exclude files matching given patterns.

    Args:
        files (list): List of file names to test.
        patterns (str): One or more strings containing forbidden patterns.

    Returns:
        list: List of filenames that did not match any of the given patterns.
    """
    result = []
    for i in range(len(files)):
        keep = True
        for pattern in patterns:
            if files[i].find(pattern) != -1:
                keep = False
        if keep:
            result += [files[i]]
    return result

#===========================================================================
def bounds(test, file, table, key, min=0, max=360, minmax=True):
    """Test whether values exeed given minimum and maximum bounds.

    Args:
        test (unittest.TestCase): Test case to evaluate against.
        file (str): Name of data file.
        table (pdsTable): PdsTable object containing the data table.
        key (tstr):
            Name of quantity to test.  If minmax==True, the "MINIMUM_" and
            "MAXIMUM_" prefixes must be omitted, and the function will add them
            and test both keys.
        min (float): Minimum allowable value.
        max (float): Maximum allowable value.
        minmax (bool): If set, both the  are "MINIMUM_" and "MAXIMUM_" keys are
                       tested.  In this case, those prefixes must be omitted
                       from the key argument.

    Returns:
        None.
    """
    if minmax:
        bounds(test, file, table, 'MINIMUM_' + key, minmax=False, min=min, max=max)
        bounds(test, file, table, 'MAXIMUM_' + key, minmax=False, min=min, max=max)
        return

    nullvals = table.info.column_info_dict[key].invalid_values.copy()
    nullval = None
    if nullvals:
        nullval = nullvals.pop()

    val = table.column_values[key]
    test.assertFalse(np.any(np.where(
        np.logical_and(
            np.logical_or(val < min, val > max), val != nullval))), (key, file))
################################################################################
