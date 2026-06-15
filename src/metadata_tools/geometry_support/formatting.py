################################################################################
# geometry_support/formatting.py - Column value formatting helpers.
#
# Config-free: depends only on oops/polymath/julian/numpy plus util, so the
# number-formatting logic can be unit-tested without the host plugin.
################################################################################
import warnings

import julian
import numpy as np
import oops
import polymath

import metadata_tools.util as util


#===============================================================================
def circle_coverage(angles, null_value, sampling, flag=None):
    """Returns inferred angular coverage, accounting for the mask.

    Args:
        angles (list, np.array, or Scalar): Angles in deg.
        null_value: Value to return when fully masked.
        sampling (int): Pixel sampling density.
        flag (str, optional):
            "-180" to return values in the range (-180,180) rather than (0,360).

    Returns:
        list: Minimum and maximum values in the cyclic array.
    """

    # Apply mask
    if isinstance(angles, polymath.Scalar):
        # Return null if fully masked
        if angles.mask is True:
            return [null_value, null_value]

        # Use full array if not masked
        if angles.mask is False:
            angles = angles.values

        # Apply mask if full mask present
        else:
            angles = angles.values[angles.antimask]

    return util._get_range_mod360(angles,
                                  width=sampling+1, diffmin=1, alt_format=flag)

#===============================================================================
def formatted_column(values, fmt, sampling):
    """Returns one formatted column (or a pair of columns) as a string.

    Args:
        values (oops.Scalar): A Scalar of values with its applied mask.
        fmt (tuple): Format tuple from FORMAT_DICT/ALT_FORMAT_DICT.
        sampling (int): Pixel sampling density.

    Returns:
        str: Formatted column.
    """

    # Interpret the format
    (flag, number_of_values, column_width,
     standard_format, overflow_format,
     null_value, valid_minimum, valid_maximum, _, _) = fmt

    # Convert from radians to degrees if necessary
    if flag in ("DEG", "360", "-180"):
        values = values * oops.DPR

    # Create a list of the numeric values for this column
    if not isinstance(values, str):
        if number_of_values == 1:
            meanval = values.mean().as_builtin()
            if isinstance(meanval, oops.Scalar) and meanval.mask:
                results = [null_value]
            else:
                results = [meanval]

        elif np.all(values.mask):
            results = [null_value, null_value]

        elif flag == "360":
            results = circle_coverage(values, null_value, sampling)

        elif flag == "-180":
            results = circle_coverage(values, null_value, sampling, flag=flag)

        else:
            results = [values.min().as_builtin(), values.max().as_builtin()]
    else:
        results = [values]

    # Convert results to ISO
    if flag in ("ISO", "iso"):
        if not isinstance(results[0], str):
            s = julian.iso_from_tai(results, digits=3)
            results = [str(s[0]), str(s[1])]

    # Write the formatted value(s)
    strings = []
    for number in results:
        error_message = ""

        # numeric values: flag common exceptions and use standard format
        if not isinstance(number, str):
            if np.isnan(number):
                warnings.warn("NaN encountered", stacklevel=2)
                number = null_value
            if np.isinf(number):
                warnings.warn("infinity encountered", stacklevel=2)
                number = null_value
            if valid_minimum != valid_maximum:
                if (number < valid_minimum) | (number > valid_maximum):
                    number = null_value
            string = standard_format % number
        # string values: left justify and enclose in double quotes
        else:
            string = '"' + number.strip('"').ljust(column_width-2) + '"'

        # handle formatting overflow
        if len(string) > column_width:
            string = overflow_format % number

            if len(string) > column_width:
                number = min(max(-9.99e99, number), 9.99e99)
                string99 = overflow_format % number

                if len(string99) > column_width:
                    error_message = "column overflow: " + string
                else:
                    warnings.warn("column overflow: " + string +
                                  " clipped to " + string99)
                    string = string99

                string = string[:column_width]

        # add the formatted value
        strings.append(string)

        if error_message != "":
            raise RuntimeError(error_message)

    return ",".join(strings)
