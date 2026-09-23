################################################################################
# geometry_support/prep.py - Row preparation for a geometry record.
################################################################################
"""Row preparation and body-prefix utilities for geometry table generation."""
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import oops
import polymath

import metadata_tools.defs as defs
from metadata_tools.geometry_support import bodies_select, formatting, masks

if TYPE_CHECKING:
    from metadata_tools.geometry_support.label_schema import ResolvedColumn
    from metadata_tools.geometry_support.record import Record


#===============================================================================
def prep_row(record: 'Record', prefixes: list[str], backplane: Any,
             blocker: str | None, columns: Sequence['ResolvedColumn'], *,
             primary: str | None = None, target: str | None = None,
             name_length: int = defs.NAME_LENGTH,
             ignore_shadows: bool = False,
             allow_zero_rows: bool = True, no_mask: bool = False,
             no_body: bool = False) -> list[list[str]]:
    """Generate the geometry and return a list of lists of strings.

    The inner list contains string representations for each column in one row of
    the output file. These will be concatenated with commas between them and
    written to the file. The outer list contains one list for each output row.

    At most one row is produced per call; if all values are null, a row is
    produced only when allow_zero_rows is False.

    Parameters:
        record: The geometry record.
        prefixes: A list of the strings to appear at the beginning of the line,
            up to and including the file specification name. Each individual
            string should already be enclosed in quotes.
        backplane: Backplane for the observation.
        blocker: The name of one body that may be able to block or shadow other
            bodies.
        columns: The table's resolved columns, in template order: each pairs a
            backplane computation with the label metadata for the values it
            writes.
        primary: Name of primary body, uppercase, e.g., "SATURN".
        target: Optionally, the target name to write into the record.
        name_length: The character width of a column to contain body names;
            default defs.NAME_LENGTH. Body names are padded or truncated to
            this width.
        ignore_shadows: True to ignore any mask constraints applicable to
            shadowing or to the sunlit faces of surfaces.
        allow_zero_rows: True to allow the function to return no rows. If False,
            a row filled with null values will be returned if necessary.
        no_mask: True to suppress the use of a mask.
        no_body: True to suppress body prefixes.

    Returns:
        The rows produced, each a list of column strings.
    """
    # Create all the needed pixel masks
    excluded_mask_dict: dict[tuple[Any, ...], polymath.Boolean] = {}
    if record.pointing_available and not no_mask:
        for column in columns:
            event_key = column.key
            mask_desc = column.mask
            mask_target = event_key[1]

            key = (mask_target,) + mask_desc
            if key in excluded_mask_dict:
                continue

            excluded_mask_dict[key] = \
                masks.construct_excluded_mask(
                            backplane, mask_target, primary, mask_desc,
                            blocker=blocker, ignore_shadows=ignore_shadows)

    # Initialize the list of columns
    prefix_columns = list(prefixes)  # make a copy

    # Append the target and system name as needed
    if not no_body:
        if target is not None:
            append_body_prefix(prefix_columns, bodies_select.get_system(target), name_length)
            append_body_prefix(prefix_columns, target, name_length)
        else:
            append_body_prefix(prefix_columns, primary, name_length)

    # Append the backplane columns
    data_columns = []
    nothing_found = True

    # For each column...
    for column in columns:
        event_key = column.key
        mask_desc = column.mask
        stubs = column.stubs
        null_flag = False

        # Fill in the backplane array
        if event_key[1] == defs.NULL:
            values: Any = oops.Scalar(0., True)
        else:
            if record.pointing_available:
                values = backplane.evaluate(event_key)
            else:
                values = oops.Scalar(0., True)
                null_flag = True

        # Make a shallow copy and apply the new mask. Use a column-local
        # target so the function's `target` parameter is not clobbered.
        if excluded_mask_dict != {}:
            col_target = event_key[1]
            excluded = excluded_mask_dict[(col_target,) + mask_desc]
            values = values.mask_where(excluded)

        if not np.all(values.mask):
            nothing_found = False

        # Save the column, formatted as its label template declares
        null_value = stubs[0].null_value
        if null_flag:
            if isinstance(null_value, str):
                values = null_value
            else:
                # resolve_schema guarantees every data column declares a null.
                values = oops.Scalar(cast(float, null_value), False)
        data_columns.append(
            formatting.formatted_column(values, stubs, record.sampling))

    # An all-null row is dropped unless the caller demands a row regardless
    if nothing_found and allow_zero_rows:
        return []

    return [prefix_columns + data_columns]

#===============================================================================
def append_body_prefix(prefix_columns: list[str], body: str | None, length: int) -> None:
    """Append a body name to the column prefixes.

    Parameters:
        prefix_columns: A list of the strings to appear at the beginning of the
            row, up to and including the file specification name. Each individual
            string should already be enclosed in quotes.
        body: Body name to append.
        length: The character width of a column to contain body names.
    """
    if body is None:
        entry = '"' + length * ' ' + '"'
    else:
        lbody = len(body)
        if lbody > length:
            entry = '"' + body[:length] + '"'
        else:
            entry = '"' + body + (length - lbody) * ' ' + '"'

    prefix_columns.append(entry)
