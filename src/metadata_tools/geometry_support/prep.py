################################################################################
# geometry_support/prep.py - Row preparation for a geometry record.
################################################################################
"""Row preparation and body-prefix utilities for geometry table generation."""
from collections.abc import Mapping, Sequence
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
             sampling: int | None = None,
             grids: Mapping[float, tuple[Any, int]] | None = None,
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
        sampling: Pixel sampling density of the backplane; by default, that of
            the record.
        grids: The backplane, and its pixel sampling density, for each
            meshgrid margin that a column declares; a column that declares
            none, or one not found here, uses *backplane*.
        ignore_shadows: True to ignore any mask constraints applicable to
            shadowing or to the sunlit faces of surfaces.
        allow_zero_rows: True to allow the function to return no rows. If False,
            a row filled with null values will be returned if necessary.
        no_mask: True to suppress the use of a mask.
        no_body: True to suppress body prefixes.

    Returns:
        The rows produced, each a list of column strings.
    """
    if sampling is None:
        sampling = record.sampling

    # Pair each column with the backplane it is sampled on
    default_grid = (backplane, sampling)
    column_grids = [default_grid if column.margin is None or not grids
                    else grids.get(column.margin, default_grid)
                    for column in columns]

    # Create all the needed pixel masks, one set for each backplane
    excluded_mask_dict: dict[tuple[Any, ...], polymath.Boolean] = {}
    if record.pointing_available and not no_mask:
        for column, (column_backplane, _sampling) in zip(columns, column_grids,
                                                         strict=True):
            event_key = column.key
            mask_desc = column.mask
            mask_target = event_key[1]

            key = (id(column_backplane), mask_target) + mask_desc
            if key in excluded_mask_dict:
                continue

            excluded_mask_dict[key] = \
                masks.construct_excluded_mask(
                            column_backplane, mask_target, primary, mask_desc,
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
    poles: dict[tuple[Any, ...], masks.Pole | None] = {}
    pole_dict: dict[tuple[Any, ...], bool] = {}

    # For each column...
    for column, (column_backplane, column_sampling) in zip(columns, column_grids,
                                                          strict=True):
        event_key = column.key
        mask_desc = column.mask
        stubs = column.stubs
        null_flag = False

        # Fill in the backplane array. A target that is not registered, such
        # as the ring system of a planet that has none, has nothing to evaluate.
        if event_key[1] == defs.NULL or not masks.target_exists(event_key[1]):
            values: Any = oops.Scalar(0., True)
        else:
            if record.pointing_available:
                values = column_backplane.evaluate(event_key)
            else:
                values = oops.Scalar(0., True)
                null_flag = True

        # Make a shallow copy and apply the new mask. Use a column-local
        # target so the function's `target` parameter is not clobbered.
        if excluded_mask_dict != {}:
            col_target = event_key[1]
            excluded = excluded_mask_dict[(id(column_backplane), col_target) + mask_desc]
            values = values.mask_where(excluded)

        if not np.all(values.mask):
            nothing_found = False

        # A visible pole of a body is an extreme of its latitude, and every
        # longitude meets there; the meshgrid samples the region around it at
        # scattered points and never on the pole itself
        complete = False
        if (event_key[0] in ('longitude', 'latitude') and record.pointing_available
                and not np.all(values.mask)):
            # The pole is located once per backplane, and its backplane shared
            # by every mask tested against it
            body_key = (id(column_backplane), event_key[1])
            if body_key not in poles:
                poles[body_key] = masks.find_pole(column_backplane, event_key[1])
            pole = poles[body_key]
            pole_desc = ('', '', '') if no_mask else mask_desc
            pole_key = body_key + pole_desc
            if pole_key not in pole_dict:
                pole_dict[pole_key] = masks.pole_in_view(
                    pole, column_backplane, event_key[1], primary, pole_desc,
                    blocker=blocker, ignore_shadows=ignore_shadows)

            if pole is not None and pole_dict[pole_key]:
                if event_key[0] == 'longitude':
                    complete = True
                elif len(stubs) == 2:
                    values = with_pole_latitude(values, pole.north)

        # Save the column, formatted as its label template declares
        null_value = stubs[0].null_value
        if null_flag:
            if isinstance(null_value, str):
                values = null_value
            else:
                # resolve_schema guarantees every data column declares a null.
                values = oops.Scalar(cast(float, null_value), False)
        data_columns.append(
            formatting.formatted_column(values, stubs, column_sampling,
                                        complete=complete))

    # An all-null row is dropped unless the caller demands a row regardless
    if nothing_found and allow_zero_rows:
        return []

    return [prefix_columns + data_columns]

#===============================================================================
def with_pole_latitude(values: Any, north: bool) -> Any:
    """Return the unmasked latitudes of a column with that of a visible pole added.

    The minimum and maximum of the result then include the pole's exact latitude,
    which no sample of a meshgrid reaches.

    Parameters:
        values: A Scalar of latitudes in radians, with its mask applied.
        north: True to add the north pole's latitude, False for the south's.

    Returns:
        An unmasked Scalar of the unmasked latitudes and the pole's.
    """
    latitudes = np.asarray(values.vals, dtype=np.float64)
    if np.any(values.mask):
        latitudes = latitudes[np.asarray(values.antimask)]
    pole_latitude = np.pi/2 if north else -np.pi/2
    return oops.Scalar(np.append(latitudes.ravel(), pole_latitude), False)

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
