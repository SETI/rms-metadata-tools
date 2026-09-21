################################################################################
# geometry_support/record.py - The Record class (one geometry table row).
################################################################################
"""Geometry record class for accumulating per-row column values."""
from collections.abc import Callable
from typing import Any, cast

import oops

import metadata_tools.columns as col
import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support import bodies_select, formats, prep


################################################################################
# Record class
################################################################################
class Record:
    """Class describing a single geometry record, i.e., a single row in a table.
    """

    #===========================================================================
    def __init__(self, observation: Any, volume_id: str, meshgrids: dict[str, Any],
                 sampling: int) -> None:
        """Construct a geometry record.

        Parameters:
            observation: OOPS Observation object.
            volume_id: Volume ID.
            meshgrids: All meshgrids associated with this host.
            sampling: Pixel sampling density.
        """
        self.observation = observation
        self.backplane_keys: dict[str, list[Any]] = {}
        config = get_geometry_config()

        # Determine primary, if any
        sclk = observation.dict["SPACECRAFT_CLOCK_START_COUNT"] + ''
        self.primary, self.secondaries, self.selections, self.additions = \
            bodies_select.get_primary(self, formats.get_mission_table(), sclk)
        self.sampling = sampling
        self.pointing_available = True

        # Column dictionaries
        self.dicts: dict[str, Any] = {
            'sky'    : col.SKY_COLUMNS,
            'sun'    : col.SUN_SUMMARY_COLUMNS,
            'ring'   : col.RING_SUMMARY_DICT,
            'body'   : col.get_body_summary_dict(),
        }

        # Set up planet-based geometry
        self.bodies: list[str] = []
        self.blocker: str | None = None

        if self.primary:
            registry = col.get_bodies_registry()
            self.rings_present: bool = registry[self.primary].ring_frame is not None

        # Determine target
        self.target = str(config.target_name(observation.dict))
        if self.target in defs._translations:
            self.target = defs._translations[self.target]

        # Create the record prefix
        filespec = observation.dict["FILE_SPECIFICATION_NAME"]
        self.prefixes = ['"' + volume_id + '"',
                         '"%-32s"' % filespec.replace(".IMG", ".LBL")]

        # Create the backplanes
        meshgrid = self._meshgrid(observation, meshgrids)
        self.backplane = oops.backplane.Backplane(observation, meshgrid)

        # Get inventory for this record
        self.inventory = bodies_select.inventory(self, col.get_bodies_registry())

        # Select bodies for this record
        self.bodies = bodies_select.select_bodies(self, col.get_bodies_registry())

        # Define a blocker body, if any
        if self.target in self.bodies:
            blocker = bodies_select.inventory(self, [self.target])
            if blocker:
                self.blocker = blocker[0]

        # Add a targeted irregular moon to the dictionary if present. The
        # assignment copies the shared cached dict first so that irregular-moon
        # targets accumulated in one Record do not leak into sibling Records or
        # persist across observations.
        if self.target in self.bodies and self.target not in self.dicts['body']:
            self.dicts['body'] = dict(self.dicts['body'])
            self.dicts['body'][self.target] = \
                util.replace(col.BODY_SUMMARY_COLUMNS, defs.BODYX, self.target)

    #===========================================================================
    @staticmethod
    def get_backplane_key(column_desc: Any) -> str:
        """Extract the backplane key from the column description.

        Parameters:
            column_desc: A column description; its first element is the event key
                (a tuple whose first element is the backplane key, or the
                backplane key itself).

        Returns:
            The backplane key.
        """

        event_key = column_desc[0]
        key = event_key[0] if isinstance(event_key, tuple) else event_key
        return cast(str, key)

    #===========================================================================
    def get_key_map(self, columns: list[str],
                    qualifier: str) -> tuple[list[Any], list[str]]:
        """Construct the mapping between backplane keys and column values.

        Parameters:
            columns: One str for each column.
            qualifier: 'sky', 'sun', 'ring', or 'body'.

        Returns:
            A tuple (backplane keys, column values).
        """

        # Get all backplane keys
        if qualifier in self.backplane_keys:
            backplane_keys = self.backplane_keys[qualifier]
        else:
            column_descs = self.dicts[qualifier]
            if isinstance(column_descs, dict):
                column_descs = column_descs[next(iter(column_descs.keys()))]

            backplane_keys = []
            for column_desc in column_descs:
                backplane_keys.append(Record.get_backplane_key(column_desc))
            self.backplane_keys[qualifier] = backplane_keys

        # Get data columns
        ndata = len(backplane_keys)
        data_columns = columns[-ndata:]

        # Create key map
        return (backplane_keys, data_columns)

    #===========================================================================
    def postprocess(self, columns: list[str], qualifier: str) -> list[str]:
        """Process the completed record.

        Parameters:
            columns: One str for each column.
            qualifier: 'sky', 'sun', 'ring', or 'body'.

        Returns:
            The processed columns.
        """

        def link_null(link: dict[str, Any], backplane_keys: list[Any],
                      data_columns: list[str]) -> list[str]:
            """Enter null value for all linked columns if any of them are null.

            Parameters:
                link: Defines the link, with key 'backplane_key' giving the
                    linked backplane key and key 'null_value' giving the null
                    value for this key.
                backplane_keys: All backplane keys.
                data_columns: Column values for each backplane key.

            Returns:
                The updated data columns.
            """
            # Locate the linked columns
            ii = [i for i, key in enumerate(backplane_keys) if key==link['backplane_key']]

            for i in range(len(ii)):
                val = data_columns[ii[i]]
                if float(val) == link['null_value']:
                    for j in range(len(ii)):
                        data_columns[ii[j]] = val
                    break

            return data_columns

        _link_dispatch: dict[str, Callable[[dict[str, Any], list[Any], list[str]], list[str]]] = {
            'null': link_null,
        }

        # Get the backplane key mapping
        backplane_keys, data_columns = self.get_key_map(columns, qualifier)

        # Build link dictionary
        links: dict[str, dict[str, Any]] = {}
        for key in backplane_keys:
            fmt = formats.FORMAT_DICT[key]
            (_,_,_,_,_, null_value, _, _, link_id, link) = fmt
            if link_id:
                links[link] = {'backplane_key' : key,
                               'null_value'    : null_value}

        # Call link functions
        for link in links:
            link_fn = _link_dispatch[link]
            data_columns = link_fn(links[link], backplane_keys, data_columns)

        # Substitute new data columns
        ndata = len(backplane_keys)
        columns[-ndata:] = data_columns

        return columns

    #===============================================================================
    def _meshgrid(self, observation: Any, meshgrids: dict[str, Any]) -> Any:
        """Look up the meshgrid for an observation.

        Parameters:
            observation: OOPS Observation object.
            meshgrids: All meshgrids associated with this host.

        Returns:
            Meshgrid for the given observation.
        """
        return get_geometry_config().meshgrid(meshgrids, observation)

    #===============================================================================
    def add(self, qualifier: str, *,
                  name: str | None = None, target: str | None = None,
                  ignore_shadows: bool = False,
                  allow_zero_rows: bool = True, no_mask: bool = False,
                  no_body: bool = False) -> list[str]:
        """Generate the geometry for one row, given a list of column descriptions.

        At most one record is produced per call; if all values are null, a record
        is produced only when allow_zero_rows is False.

        Parameters:
            qualifier: 'sky', 'sun', 'ring', or 'body'.
            name: Name identifying a specific column description.
            target: Optionally, the target name to write into the record.
            ignore_shadows: True to ignore any mask constraints applicable to
                shadowing or to the sunlit faces of surfaces.
            allow_zero_rows: True to allow the function to return no rows. If
                False, a row filled with null values will be returned if
                necessary.
            no_mask: True to suppress the use of a mask.
            no_body: True to suppress body prefixes.

        Returns:
            The formatted output rows.
        """
        # Get the column descriptions
        column_descs = self.dicts[qualifier]
        if name:
            column_descs = column_descs[name]

        # Prepare the rows
        rows, _overrides = prep.prep_row(self, self.prefixes, self.backplane, self.blocker,
                                column_descs,
                                primary=self.primary, target=target,
                                ignore_shadows=ignore_shadows,
                                allow_zero_rows=allow_zero_rows,
                                no_mask=no_mask,
                                no_body=no_body)

        # Postprocess the rows and append to the output
        lines: list[str] = []
        for columns in rows:
            row = self.postprocess(columns, qualifier)
            lines.append(','.join(row))

        return lines
