################################################################################
# geometry_support/record.py - The Record class (one geometry table row).
################################################################################
import geometry_config as config
import oops

import metadata_tools.columns as col
import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.geometry_support import bodies_select, formats, prep


################################################################################
# Record class
################################################################################
class Record(object):
    """Class describing a single geometry record, i.e., a single row in a table.
    """

    #===========================================================================
    def __init__(self, observation, volume_id, meshgrids, sampling, level):
        """Constructor for a geometry record.

        Args:
            observation (oops.Observation): OOPS Observation object.
            volume_id (str): Volume ID.
            meshgrids (dict): All meshgrids associated with this host.
            sampling (int): Pixel sampling density.
            level (str, optional): Processing level: 'summary' or 'detailed'.
        """
        self.observation = observation
        self.backplane_keys = {}

        # Determine primary, if any
        sclk = observation.dict["SPACECRAFT_CLOCK_START_COUNT"] + ''
        self.primary, self.secondaries, self.selections, self.additions = \
            bodies_select.get_primary(self, formats.MISSION_TABLE, sclk)
        self.level = level
        self.sampling = sampling
        self.pointing_available = True

        # Level-specific column dictionaries
        self.dicts = {'sky' : col.SKY_COLUMNS}
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
        self.bodies = []
        self.blocker = None

        if self.primary:
            self.rings_present = col.BODIES[self.primary].ring_frame is not None
            self.ring_tile_dict = col.RING_TILE_DICT[self.primary]
            self.body_tile_dict = col.BODY_TILE_DICT[self.primary]

        # Determine target
        self.target = str(config.target_name(observation.dict))
        if self.target in defs.TRANSLATIONS.keys():
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
        if self.target in self.bodies and self.target not in self.dicts['body'].keys():
            self.dicts['body'][self.target] = \
                util.replace(col.BODY_SUMMARY_COLUMNS,
                                defs.BODYX, self.target)
            self.body_tile_dict[self.target] = \
                util.replace(col.BODY_TILES,
                                defs.BODYX, self.target)

    #===========================================================================
    @staticmethod
    def get_backplane_key(column_desc):
        """Extract the backplane key from the column description.

        Args:
            column_desc (dict or list): .

        Returns:
            None
        """

        event_key = column_desc[0]
        return event_key[0] if isinstance(event_key, tuple) else event_key

    #===========================================================================
    def get_key_map(self, columns, qualifier):
        """Construct the mapping between backplane keys and column values.

        Args:
            columns (list): One str for each column.
            qualifier: 'sky', 'sun', 'ring', or 'body'.

        Returns:
            list: tuples of (backplane key, column value)
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
    def postprocess(self, columns, qualifier):
        """Process the completed record.

        Args:
            columns (list): One str for each column.
            qualifier (str): 'sky', 'sun', 'ring', or 'body'.

        Returns:
            None
        """

        def link_null(link, backplane_keys, data_columns):
            """Enter null value for all linked columns if any of them are null.

            Args:
                link (dict): Defines the link:
                                 backplane_key : Linked backplane key.
                                 null_value    : Null value for this key.
                backplane_keys (list): All backplane keys.
                data_columns (list): Column values for each backplane key.

            Returns:
                Update data columns
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
        links = {}
        for key in backplane_keys:
            format = formats.FORMAT_DICT[key]
            (_,_,_,_,_, null_value, _, _, link_id, link) = format
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
    def _meshgrid(self, observation, meshgrids):
        """Looks up the meshgrid for an observation.

        Args:
            observation (oops.Observation): OOPS Observation object.
            meshgrids (dict): All meshgrids associated with this host.

        Returns:
            oops.Meshgrid: Meshgrid for the given observation.
        """
        return config.meshgrid(meshgrids, observation)

    #===============================================================================
    def add(self, qualifier, *,
                  name=None, target=None, tiles=None, tiling_min=100,
                  ignore_shadows=False, start_index=1, allow_zero_rows=True,
                  no_mask=False, no_body=False):
        """Generates the geometry for one row, given a list of column descriptions.

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

        Args:
            qualifier: 'sky', 'sun', 'ring', or 'body'.
            name (str, optional): Name identifying a specific column description.
            target (str, optional): Optionally, the target name to write into the record.
            tiles (list, optional):
                An optional list of boolean backplane keys, used to
                support the generation of detailed tabulations instead
                of summary tabulations. See details above.
            tiling_min (int, optional):
                The lower limit on the number of meshgrid points in a
                region before that region is subdivided into tiles.
            ignore_shadows (bool, optional):
                True to ignore any mask constraints applicable to
                shadowing or to the sunlit faces of surfaces.
            start_index (int, optional): Index to use for first subregion. Default 1.
            allow_zero_rows (bool, optional):
                True to allow the function to return no rows. If False,
                a row filled with null values will be returned if
                necessary.
            no_mask (bool, optional): True to suppress the use of a mask.
            no_body (bool, optional): True to suppress body prefixes.
        """
        if tiles is None:
            tiles = []

        # Get the column descriptions
        column_descs = self.dicts[qualifier]
        if name:
            column_descs = column_descs[name]

        # Prepare the rows
        rows, overrides = prep.prep_row(self, self.prefixes, self.backplane, self.blocker,
                                column_descs,
                                primary=self.primary, target=target,
                                tiles=tiles, tiling_min=tiling_min,
                                ignore_shadows=ignore_shadows,
                                start_index=start_index, allow_zero_rows=allow_zero_rows,
                                no_mask=no_mask,
                                no_body=no_body)
#        self.overrides += overrides  ## this is for future development

        # Postprocess the rows and append to the output
        lines = []
        for columns in rows:
            row = self.postprocess(columns, qualifier)
            lines.append(','.join(row))

        return lines
