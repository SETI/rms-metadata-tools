################################################################################
# geometry_support/formatting.py - Column value formatting helpers.
#
# Config-free: depends only on oops/polymath/julian/numpy plus util, so the
# number-formatting logic can be unit-tested without the host plugin.
################################################################################
"""Column value formatting utilities for geometry tables."""
import warnings
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

import julian
import numpy as np
import oops
import polymath

import metadata_tools.util as util

if TYPE_CHECKING:
    from metadata_tools.geometry_support.label_schema import ColumnStub


#===============================================================================
def circle_coverage(angles: Any, null_value: float | str, sampling: int,
                    flag: str | None = None) -> list[Any]:
    """Return inferred angular coverage, accounting for the mask.

    Parameters:
        angles: Angles in deg, as a list, np.array, or Scalar.
        null_value: Value to return when fully masked.
        sampling: Pixel sampling density.
        flag: "-180" to return values in the range (-180,180) rather than
            (0,360).

    Returns:
        Minimum and maximum values in the cyclic array.
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
            angles = np.asarray(angles.values)[angles.antimask]

    return util._get_range_mod360(angles,
                                  width=sampling+1, diffmin=1, alt_format=flag)

#===============================================================================
def formatted_column(values: Any, overflow_format: str | None,
                     stubs: Sequence['ColumnStub'], sampling: int) -> str:
    """Return one formatted column (or a pair of columns) as a string.

    Parameters:
        values: A Scalar of values with its applied mask (or a string).
        overflow_format: The print format substituted when a value will not fit
            its field, or None when the column cannot overflow. PDS3 cannot
            express a fallback format, so this is the one piece of formatting
            the catalog still supplies.
        stubs: The label metadata for each value this column writes, in slot
            order; its length is the number of values. The unit conversion,
            width, print format, null value, and valid range all come from
            here, which is to say from the host's label template.
        sampling: Pixel sampling density.

    Returns:
        Formatted column.

    Raises:
        RuntimeError: If a formatted value overflows the column width and cannot
            be clipped to fit.
    """

    # Interpret the format. The conversion flag is derived from the label, so
    # every slot of a column carries the same one; resolve_schema checks that.
    flag = stubs[0].flag
    number_of_values = len(stubs)
    # A column's slots share one null value; per-slot nulls are applied below.
    # resolve_schema guarantees every data column declares a null.
    null_value = cast('float | str', stubs[0].null_value)

    # Convert from radians to degrees if necessary
    if flag in ("DEG", "360", "-180"):
        values = values * oops.DPR

    # Create a list of the numeric values for this column
    results: list[Any]
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
        # A string value is the column's null, substituted upstream when
        # pointing is unavailable. Every slot gets one: emitting a single field
        # for a two-slot column would short the row and shift every column
        # after it.
        results = [values] * number_of_values

    # Convert results to ISO
    if flag in ("ISO", "iso"):
        if not isinstance(results[0], str):
            s = julian.iso_from_tai(results, digits=3)
            results = [str(s[0]), str(s[1])]

    # Write the formatted value(s)
    strings: list[str] = []
    for stub, entry in zip(stubs, results, strict=True):
        number: Any = entry
        column_width = stub.width
        error_message = ""
        string: str

        # numeric values: flag common exceptions and use standard format
        if not isinstance(number, str):
            if np.isnan(number):
                warnings.warn("NaN encountered", stacklevel=2)
                number = stub.null_value
            if np.isinf(number):
                warnings.warn("infinity encountered", stacklevel=2)
                number = stub.null_value
            # A template that declares no range asks for no range check; the
            # old sentinel for that was valid_minimum == valid_maximum.
            if stub.valid_minimum is not None and stub.valid_maximum is not None:
                if (number < stub.valid_minimum) | (number > stub.valid_maximum):
                    number = stub.null_value
            string = stub.print_format % number
        # string values: left justify and enclose in double quotes
        else:
            string = '"' + number.strip('"').ljust(column_width-2) + '"'

        # handle formatting overflow
        if len(string) > column_width:
            # An overflow format is always defined for columns that can overflow.
            overflow = cast(str, overflow_format)
            string = overflow % number

            if len(string) > column_width:
                number = min(max(-9.99e99, number), 9.99e99)
                string99 = overflow % number

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
