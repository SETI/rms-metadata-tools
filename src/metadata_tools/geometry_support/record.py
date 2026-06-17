################################################################################
# geometry_support/record.py - The Record class (one geometry table row).
################################################################################
from typing import Any, cast

import geometry_config as config
import oops

import metadata_tools.columns as col
import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.geometry_support import bodies_select, formats, prep


################################################################################
# Record class
################################################################################
class Record:
    """Class describing a single geometry record, i.e., a single row in a table.
    """

    #===========================================================================
    def __init__(self, observation: Any, volume_id: str, meshgrids: dict[str, Any],
                 sampling: int, level: str) -> None:
        """Construct a geometry record.

        Parameters:
            observation: OOPS Observation object.
            volume_id: Volume ID.
            meshgrids: All meshgrids associated with this host.
            sampling: Pixel sampling density.
            level: Processing level: 'summary' or 'detailed'.
        """
        self.observation = observation
        self.backplane_keys: dict[str, list[Any]] = {}

        # Determine primary, if any
        sclk = observation.dict["SPACECRAFT_CLOCK_START_COUNT"] + ''
        self.primary, self.secondaries, self.selections, self.additions = \
            bodies_select.get_primary(self, formats.MISSION_TABLE, sclk)
        self.level = level
        self.sampling = sampling
        self.pointing_available = True

        # Level-specific column dictionaries
        self.dicts: dict[str, Any] = {'sky' : col.SKY_COLUMNS}
        if level == 'summary':
            self.dicts |= {
                'sun'    : col.SUN_SUMMARY_COLUMNS,
                'ring'   : col.RING_SUMMARY_DICT,
                'body'   : col.BODY_SUMMARY_DICT,
            }
        else:
            self.dicts |= {
                'sun'    : col.SUN_DETAILED_COLUMNS,
                'ring'   : col.RING_DETAILED_DICT,
                'body'   : col.BODY_DETAILED_DICT
            }

        # Set up planet-based geometry
        self.bodies: list[str] = []
        self.blocker: str | None = None

        if self.primary:
            self.rings_present: bool = col.BODIES[self.primary].ring_frame is not None
            self.ring_tile_dict: Any = col.RING_TILE_DICT[self.primary]
            self.body_tile_dict: Any = col.BODY_TILE_DICT[self.primary]

        # Determine target
        self.target = str(config.target_name(observation.dict))
        if self.target in defs.TRANSLATIONS:
            self.target = defs.TRANSLATIONS[self.target]

        # Create the record prefix
        filespec = observation.dict["FILE_SPECIFICATION_NAME"]
        self.prefixes = ['"' + volume_id + '"',
                         '"%-32s"' % filespec.replace(".IMG", ".LBL")]

        # Create the backplanes
        meshgrid = self._meshgrid(observation, meshgrids)
        self.backplane = oops.backplane.Backplane(observation, meshgrid)

        # Get inventory for this record
        self.inventory = bodies_select.inventory(self, col.BODIES)

        # Select bodies for this record
        self.bodies = bodies_select.select_bodies(self, col.BODIES)

        # Define a blocker body, if any
        if self.target in self.bodies:
            blocker = bodies_select.inventory(self, [self.target])
            if blocker:
                self.blocker = blocker[0]

        # Add a targeted irregular moon to the dictionaries if present
        if self.target in self.bodies and self.target not in self.dicts['body']:
            self.dicts['body'][self.target] = \
                util.replace(col.BODY_SUMMARY_COLUMNS,
                                defs.BODYX, self.target)
            self.body_tile_dict[self.target] = \
                util.replace(cast(list[Any], col.BODY_TILES),
                                defs.BODYX, self.target)

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
            link_fn = locals()['link_' + link]
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
        return config.meshgrid(meshgrids, observation)

    #===============================================================================
    def add(self, qualifier: str, *,
                  name: str | None = None, target: str | None = None,
                  tiles: list[Any] | tuple[Any, ...] | None = None, tiling_min: int = 100,
                  ignore_shadows: bool = False, start_index: int = 1,
                  allow_zero_rows: bool = True, no_mask: bool = False,
                  no_body: bool = False) -> list[str]:
        """Generate the geometry for one row, given a list of column descriptions.

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
        used to ensure that tiling is suppressed when the region to be tiled is too
        small. If the number of meshgrid samples that are equal to True in this
        backplane is smaller than the limit specified by argument tiling_min, then
        no detailed record is written.

        In a summary listing, this routine writes one record per call, even if all
        values are null. In a detailed listing, only records associated with
        non-empty regions of the meshgrid are written.

        Parameters:
            qualifier: 'sky', 'sun', 'ring', or 'body'.
            name: Name identifying a specific column description.
            target: Optionally, the target name to write into the record.
            tiles: An optional list of boolean backplane keys, used to support
                the generation of detailed tabulations instead of summary
                tabulations. See details above.
            tiling_min: The lower limit on the number of meshgrid points in a
                region before that region is subdivided into tiles.
            ignore_shadows: True to ignore any mask constraints applicable to
                shadowing or to the sunlit faces of surfaces.
            start_index: Index to use for first subregion. Default 1.
            allow_zero_rows: True to allow the function to return no rows. If
                False, a row filled with null values will be returned if
                necessary.
            no_mask: True to suppress the use of a mask.
            no_body: True to suppress body prefixes.

        Returns:
            The formatted output rows.
        """
        if tiles is None:
            tiles = []

        # Get the column descriptions
        column_descs = self.dicts[qualifier]
        if name:
            column_descs = column_descs[name]

        # Prepare the rows
        rows, _overrides = prep.prep_row(self, self.prefixes, self.backplane, self.blocker,
                                column_descs,
                                primary=self.primary, target=target,
                                tiles=tiles, tiling_min=tiling_min,
                                ignore_shadows=ignore_shadows,
                                start_index=start_index, allow_zero_rows=allow_zero_rows,
                                no_mask=no_mask,
                                no_body=no_body)
#        self.overrides += overrides  ## this is for future development

        # Postprocess the rows and append to the output
        lines: list[str] = []
        for columns in rows:
            row = self.postprocess(columns, qualifier)
            lines.append(','.join(row))

        return lines
