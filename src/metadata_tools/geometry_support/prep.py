################################################################################
# geometry_support/prep.py - Row preparation for a geometry record.
################################################################################
from typing import TYPE_CHECKING, Any

import numpy as np
import oops

import metadata_tools.defs as defs
from metadata_tools.geometry_support import bodies_select, formats, formatting, masks

if TYPE_CHECKING:
    from metadata_tools.geometry_support.record import Record


#===============================================================================
def prep_row(record: 'Record', prefixes: list[str], backplane: Any,
             blocker: str | None, column_descs: Any, *,
             primary: str | None = None, target: str | None = None,
             name_length: int = defs.NAME_LENGTH,
             tiles: list[Any] | tuple[Any, ...] | None = None, tiling_min: int = 100,
             ignore_shadows: bool = False, start_index: int = 1,
             allow_zero_rows: bool = True, no_mask: bool = False,
             no_body: bool = False) -> tuple[list[list[str]], list[list[dict[str, Any]]]]:
    """Generates the geometry and returns a list of lists of strings. The inner
    list contains string representations for each column in one row of the
    output file. These will be concatenated with commas between them and written
    to the file. The outer list contains one list for each output row. The
    number of output rows can be zero or more.

    The tiles argument supports detailed listings where a geometric region is
    broken down into separate subregions. If the tiles argument is empty (which
    is the default), then this routine writes a summary file.

    If the tiles argument is not empty, then the routine writes a detailed file,
    which generally contains one record for each non-empty subregion. The tiles
    argument must be a list of boolean backplane keys, each equal to True for
    the pixels within the subregion. An additional column is added before the
    geometry columns, containing the index value of the associated tile.

    The first backplane in the list is treated differently. It should evaluate
    to an area roughly equal to the union of all the other backplanes. It is
    used as an overlay to all subsequent tiles.

    In a summary listing, this routine writes one record per call, even if all
    values are null. In a detailed listing, only records associated with
    non-empty regions of the meshgrid are written.

    Args:
        record: The geometry record.
        prefixes:
            A list of the strings to appear at the beginning of the
            line, up to and including the file specification name. Each
            individual string should already be enclosed in quotes.
        backplane: Backplane for the observation.
        blocker:
            The name of one body that may be able to block or shadow
            other bodies.
        column_descs: A list of column descriptions.
        primary: Name of primary body, uppercase, e.g., "SATURN".
        target: Optionally, the target name to write into the record.
        name_length:
            The character width of a column to contain body names.
            If zero (which is the default), then no name is
            written into the record.
        tiles:
            An optional list of boolean backplane keys, used to
            support the generation of detailed tabulations instead
            of summary tabulations. See details above.
        tiling_min:
            The lower limit on the number of meshgrid points in a
            region before that region is subdivided into tiles.
        ignore_shadows:
            True to ignore any mask constraints applicable to
            shadowing or to the sunlit faces of surfaces.
        start_index: Index to use for first subregion. Default 1.
        allow_zero_rows:
            True to allow the function to return no rows. If False,
            a row filled with null values will be returned if
            necessary.
        no_mask: True to suppress the use of a mask.
        no_body: True to suppress body prefixes.

    Returns:
        A tuple (rows, overrides), where:
            rows: Strings comprising the resulting rows.
            overrides: Dicts of column entries to override in label. One dict for
                       each column, not including prefix columns.
    """
    if tiles is None:
        tiles = []

    # Handle option for multiple tile sets
    if isinstance(tiles, tuple):
        rows: list[list[str]] = []
        overrides: list[list[dict[str, Any]]] = []
        local_index = start_index
        for tile in tiles:
            new_rows, new_overrides = prep_row(
                record, prefixes, backplane, blocker, column_descs,
                primary=primary, target=target, name_length=name_length,
                tiles=tile, tiling_min=tiling_min, ignore_shadows=ignore_shadows,
                start_index=local_index, allow_zero_rows=True,
                no_mask=no_mask, no_body=no_body)
            rows += new_rows
            overrides += new_overrides
            local_index += len(tile) - 1

        if rows or allow_zero_rows:
            return (rows, overrides)

        return prep_row(
            record, prefixes, backplane, blocker, column_descs,
            primary=primary, target=target, name_length=name_length,
            tiles=[], tiling_min=tiling_min, ignore_shadows=ignore_shadows,
            start_index=start_index, allow_zero_rows=False,
            no_mask=no_mask, no_body=no_body)

    # Handle a single set of tiles
    subregion_masks: list[Any]
    if tiles:
        global_area = backplane.evaluate(tiles[0]).vals
        subregion_masks = [np.logical_not(global_area)]

        if global_area.sum() < tiling_min:
            tiles = []
        else:
            for tile in tiles[1:]:
                mask = backplane.evaluate(tile).vals & global_area
                subregion_masks.append(np.logical_not(mask))
    else:
        subregion_masks = []

    # Initialize the list of rows
    rows = []
    overrides = []

    # Create all the needed pixel masks
    excluded_mask_dict: dict[tuple[Any, ...], Any] = {}
    if record.pointing_available and not no_mask:
        for column_desc in column_descs:
            event_key = column_desc[0]
            mask_desc = column_desc[1]
            mask_target = event_key[1]

            key = (mask_target,) + mask_desc
            if key in excluded_mask_dict:
                continue

            excluded_mask_dict[key] = \
                masks.construct_excluded_mask(
                            backplane, mask_target, primary, mask_desc,
                            blocker=blocker, ignore_shadows=ignore_shadows)

    # Interpret the subregion list
    indices: range | list[int]
    if tiles:
        indices = range(1, len(tiles))
    else:
        indices = [0]

    # For each subregion...
    for indx in indices:

        # Skip a subregion if it will be empty
        if indx != 0 and np.all(subregion_masks[indx]):
            continue

        # Initialize the list of columns
        prefix_columns = list(prefixes)  # make a copy

        # Append the target and system name as needed
        if not no_body:
            if target is not None:
                append_body_prefix(prefix_columns, bodies_select.get_system(target), name_length)
                append_body_prefix(prefix_columns, target, name_length)
            else:
                append_body_prefix(prefix_columns, primary, name_length)

        # Insert the subregion index
        if subregion_masks:
            prefix_columns.append('%2d' % (indx + start_index - 1))

        # Append the backplane columns
        data_columns = []
        row_overrides = []
        nothing_found = True

        # For each column...
        for column_desc in column_descs:
            event_key = column_desc[0]
            mask_desc = column_desc[1]
            null_flag = False

            # Fill in the backplane array
            if event_key[1] == defs.NULL:
                values = oops.Scalar(0., True)
            else:
                if record.pointing_available:
                    values = backplane.evaluate(event_key)
                else:
                    values = oops.Scalar(0., True)
                    null_flag = True

            # Make a shallow copy and apply the new masks. Use a column-local
            # target so the function's `target` parameter is not clobbered.
            if excluded_mask_dict != {}:
                col_target = event_key[1]
                excluded = excluded_mask_dict[(col_target,) + mask_desc]
                values = values.mask_where(excluded)
                if len(subregion_masks) > 1:
                    values = values.mask_where(subregion_masks[indx])
                elif len(subregion_masks) == 1:
                    values = values.mask_where(subregion_masks[0])

            if not np.all(values.mask):
                nothing_found = False

            # Save the column using the specified format
            if len(column_desc) > 2:
                fmt = formats.ALT_FORMAT_DICT[(event_key[0], column_desc[2])]
            else:
                fmt = formats.FORMAT_DICT[event_key[0]]

            (_,_,_,_,_, null_value, valid_minimum, valid_maximum, _, _) = fmt
            if null_flag:
                if isinstance(null_value, str):
                    values = null_value
                else:
                    values = oops.Scalar(null_value, False)
            data_columns.append(formatting.formatted_column(values, fmt, record.sampling))

            # Save this column's label override.
            row_overrides.append({'NULL_VALUE': null_value,
                                  'VALID_MINIMUM': valid_minimum,
                                  'VALID_MAXIMUM': valid_maximum})

        # Save the row if it was completed
        if len(data_columns) < len(column_descs):
            continue  # hopeless error
        if nothing_found and (indx > 0 or allow_zero_rows):
            continue
        rows.append(prefix_columns + data_columns)
        overrides.append(row_overrides)

    # Return something if we can
    if rows or allow_zero_rows:
        return (rows, overrides)

    return prep_row(
        record, prefixes, backplane, blocker, column_descs,
        primary=primary, target=target, name_length=name_length,
        tiles=[], tiling_min=0, ignore_shadows=ignore_shadows,
        start_index=start_index, allow_zero_rows=False,
        no_mask=no_mask, no_body=no_body)

#===============================================================================
def append_body_prefix(prefix_columns: list[str], body: str | None, length: int) -> None:
    """Append a body name to the column prefixes.

    Args:
        prefix_columns:
            A list of the strings to appear at the beginning of the
            row, up to and including the file specification name. Each
            individual string should already be enclosed in quotes.
        body: Body name to append.
        length:
            The character width of a column to contain body names.
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
