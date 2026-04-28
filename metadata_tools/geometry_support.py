################################################################################
# geometry_support.py - Tools for generating geometry tables.
################################################################################
import re
import oops
import julian
import numpy as np
import traceback
import warnings
import fnmatch
import polymath

import metadata_tools.common as com
import metadata_tools.util as util
import metadata_tools.defs as defs
import metadata_tools.columns as col

from filecache import FCPath

import geometry_config as config

################################################################################
# FORMAT_DICT tuples are:
#
#   (flag, number_of_values, column_width, standard_format, overflow_format,
#    null_value, valid_minimum, valid_maximum, link_id, link)
#
# where...
#
#   flag = "RAD" = convert values from radians to degrees;
#        = "360" = convert to degrees, with 360-deg periodicity;
#        = ""    = do not modify value.
#
#   link_id is a positive integer id that can be used to link multiple columns via
#   the specified link function. All columns with the same link function and 
#   link id are linked together.
#
# Note null_value, valid_minimum, valid_maximum are tracked in the override dicts, but
# not currently used to populate the label, which would remove the redundancy of 
# specifying them separately in the both the format dict and the label template.
#
# Adding a geometry column:
#   1. Add a column definition to column definition file, e.g. COLUMNS_BODY.py.
#   2. Add a corresponding function to appropriate backplane module.
#   3. Add a row to the format dictionary below.
#   4. Add column description(s) to the label template, e.g., body_summary.lbl.
#   5. Run the host-specific geometry program, e.g., GO_xxxx_geometry.py.
#   6. Update the unit tests.
#
################################################################################
FORMAT_DICT = {
    "right_ascension"           : ("360", 2, 10, "%10.6f", "%10.5f", -999., 0, 360, 0, ''),
    "center_right_ascension"    : ("360", 2, 10, "%10.6f", "%10.5f", -999., 0, 360, 0, ''),
    "declination"               : ("DEG", 2, 10, "%10.6f", "%10.5f", -999., -90, 90, 0, ''),
    "center_declination"        : ("DEG", 2, 10, "%10.6f", "%10.5f", -999., -90, 90, 0, ''),

    "distance"                  : ("",    2, 12, "%12.3f", "%12.5e", -999., 0, 0, 0, ''),
    "center_distance"           : ("",    2, 12, "%12.3f", "%12.5e", -999., 0, 0, 0, ''),
    "center_coordinate"         : ("",    1, 12, "%12.3f", "%12.5e", -99999, -10000, 10000, 1, 'null'),
    "radius_in_pixels"          : ("",    2, 12, "%12.3f", "%12.5e", -999., 0, 0, 0, ''),

    "ring_radius"               : ("",    2, 12, "%12.3f", "%12.5e", -999., 0, 0, 0, ''),
    "ansa_radius"               : ("",    2, 12, "%12.3f", "%12.5e", -999., 0, 0, 0, ''),

    "altitude"                  : ("",    2, 12, "%12.3f", "%12.5e", -99999., 0, 0, 0, ''),
    "ansa_altitude"             : ("",    2, 12, "%12.3f", "%12.5e", -9.99e+09, 0, 0, 0, ''),

    "resolution"                : ("",    2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),
    "finest_resolution"         : ("",    2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),
    "coarsest_resolution"       : ("",    2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),
    "ring_radial_resolution"    : ("",    2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),

    "ansa_radial_resolution"    : ("",    2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),
    "ansa_vertical_resolution"  : ("",    2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),
    "center_resolution"         : ("",    2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),
    "body_diameter_in_pixels"   : ("",    1, 12, "%12.3f", "%12.5e", -999., 0, 0, 0, ''),

    "event_time"                : ("ISO", 2, 25, "%25s", "%25s", '"NA"', 0, 0, 0, ''),

    "ring_angular_resolution"   : ("DEG", 2, 10, "%10.5f",  "%6.3e", -999., 0, 0, 0, ''),

    "longitude"                 : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "ring_longitude"            : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "ring_azimuth"              : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "ansa_longitude"            : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "sub_solar_longitude"       : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "sub_observer_longitude"    : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "ring_sub_solar_longitude"  : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "ring_sub_observer_longitude"
                                : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),

    "latitude"                  : ("DEG", 2,  8, "%8.3f",  None,     -999., -90, 90, 0, ''),
    "sub_solar_latitude"        : ("DEG", 2,  8, "%8.3f",  None,     -999., -90, 90, 0, ''),
    "sub_observer_latitude"     : ("DEG", 2,  8, "%8.3f",  None,     -999., -90, 90, 0, ''),

    "limb_altitude"             : ("",    2, 12, "%12.3f", "%12.5e", -99999., 0, 0, 0, ''),
    "limb_clock_angle"          : ("360", 2,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),

    "pole_clock_angle"          : ("DEG", 1,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),
    "pole_position_angle"       : ("DEG", 1,  8, "%8.3f",  None,     -999., 0, 360, 0, ''),

    "phase_angle"               : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 180, 0, ''),
    "center_phase_angle"        : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 180, 0, ''),
    "incidence_angle"           : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 180, 0, ''),
    "ring_incidence_angle"      : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 180, 0, ''),
    "center_incidence_angle"    : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 90, 0, ''),
    "ring_center_incidence_angle"
                                : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 180, 0, ''),
    "emission_angle"            : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 90, 0, ''),
    "ring_emission_angle"       : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 180, 0, ''),
    "center_emission_angle"     : ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 90, 0, ''),
    "ring_center_emission_angle": ("DEG", 2,  8, "%8.3f",  None,     -999., 0, 180, 0, ''),
    "ring_elevation"            : ("DEG", 2,  8, "%8.3f",  None,     -999., -90, 90, 0, ''),

    "where_inside_shadow"       : ("",    2,  1, "%1d",    None,        0, 0, 0, 0, ''),
    "where_in_front"            : ("",    2,  1, "%1d",    None,        0, 0, 0, 0, ''),
    "where_in_back"             : ("",    2,  1, "%1d",    None,        0, 0, 0, 0, ''),
    "where_antisunward"         : ("",    2,  1, "%1d",    None,        0, 0, 0, 0, '')}

ALT_FORMAT_DICT = {
    ("ring_angular_resolution", "km")
                                : ("KM",   2, 10, "%10.5f", "%10.4e", -999., 0, 0, 0, ''),
    ("longitude",      "-180")  : ("-180", 2, 8, "%8.3f",  None,     -999., -180, 180, 0, ''),
    ("ring_longitude", "-180")  : ("-180", 2, 8, "%8.3f",  None,     -999., -180, 180, 0, ''),
    ("sub_longitude",  "-180")  : ("-180", 2, 8, "%8.3f",  None,     -999., -180, 180, 0, '')}

MISSION_TABLE = \
    util.convert_mission_table(config.MISSION_TABLE, config.SC)

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
            self._get_primary(MISSION_TABLE, sclk)
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
                'ring'   : col.RING_SUMMARY_DETAILED,
                'body'   : col.BODY_SUMMARY_DETAILED
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
        self.inventory = self._inventory(col.BODIES)

        # Select bodies for this record
        self.bodies = Record._select_bodies(self, col.BODIES)

        # Define a blocker body, if any
        if self.target in self.bodies:
            blocker = self._inventory([self.target])
            if blocker:
                self.blocker = blocker[0]

        # Add a targeted irregular moon to the dictionaries if present
        if self.target in self.bodies and self.target not in self.dicts['body'].keys():
            self.dicts['body'][self.target] = \
                util.replace(col.BODY_SUMMARY_COLUMNS,
                                defs.BODYX, self.target)
            self.body_tile_dict[self.target] = \
                util.replace(col.BODY_TILES,
                                col.BODYX, self.target)

    #===============================================================================
    def _inventory(self, bodies):
        """Obtain image inventory if possible.

        Args:
            bodies (list): Bodies to test.

        Returns:
            List of inventory bodies.
        """
        logger = com.get_logger()

        # Attempt to obtain inventory
        try:
            inventory = self.observation.inventory(bodies, expand=config.EXPAND, cache=False)
            return inventory

        # A RuntimeError is probably caused by missing spice data. There is
        # probably nothing we can do.
        except (OSError, RuntimeError) as e:
            error = str(e)

            # If no C-kernel data for this observation, proceed with a warning and set the 
            # pointing_available flag.
            if 'SPICE(NOFRAMECONNECT)' in error or 'SPICE(CKINSUFFDATA)' in error:
                logger.warning(str(e))
                self.pointing_available = False
            # Other kinds of errors are genuine bugs.
            else:
                logger.exception("Unexpected error during inventory")
            return []

        # Other kinds of errors are genuine bugs.
        except (AssertionError, AttributeError, IndexError, KeyError,
                LookupError, TypeError, ValueError):
            logger.exception("Unexpected error during inventory")
            return []

    #===============================================================================
    def _select_bodies(self, bodies):
        """Select all bodies to include in this record according to the following rules:
        
           1. The primary and secondary bodies are always included. 
           2. Children of the primary are included if they intersect the FOV. If there are
              selections, then only the selected children are considered.
           3. If there is no primary, all selections that intersect the FOV are included.
           4. The target is always included. 
           5. If the target is a satellite, the parent is included.
           6. Additions are included whenever they intersect the FOV, regardless of the 
              primary.

        Args:
            bodies (list): All bodies.

        Returns:
            List of selected bodies.
        """

        # Add bodies
        body_names = []

        # Add primary body and FOV/selected children
        if self.primary:
            body_names += [self.primary]
            children = [child.name for child in col.BODIES[self.primary].children
                            if child.name in bodies.keys()]
            children = self._inventory(children)
            if self.selections:
                children = list(set(children) & set(self.selections))
            body_names += children
        # Add all FOV selections if no primary
        else:
            body_names += self._inventory(self.selections)

        # Add any secondary bodies
        if self.secondaries:
            body_names += self.secondaries

        # Add any additions in the FOV
        if self.additions:
            body_names += self._inventory(self.additions)

        # Add target body and parent
        if self.target and oops.Body.exists(self.target):
            system = self._get_system(self.target)
            if system: 
                body_names += [system]
            body_names += [self.target]

        # Cull duplicate bodies and verify all bodies are in the registry
        body_names = list(dict.fromkeys(body_names))

        # Sort bodies based on occurence in BODIES list
        body_names.sort(key=lambda name : list(col.BODIES.keys()).index(name))

        return [body_name for body_name in body_names if oops.Body.exists(body_name)]

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
            format = FORMAT_DICT[key]
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
    def _get_system(self, body):
        """Looks up the meshgrid for an observation.

        Args:
            body (str): Body for which to determine the system.  For a satellite, the
                        system is the parent.  For planet, the system is itself.

        Returns:
            str: Name of system, body.
        """
        if body in oops.Body.BODY_REGISTRY:
            parent = oops.Body.BODY_REGISTRY[body].parent.name
        else:
            return None
        if parent != 'SUN':
            return parent
        return body

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
        rows, overrides = self._prep_row(self.prefixes, self.backplane, self.blocker, column_descs,
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

    #===============================================================================
    def _prep_row(self, prefixes, backplane, blocker, column_descs, *,
                  primary=None, target=None, name_length=defs.NAME_LENGTH,
                  tiles=None, tiling_min=100, ignore_shadows=False,
                  start_index=1, allow_zero_rows=True, no_mask=False,
                  no_body=False):
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
            prefixes (list):
                A list of the strings to appear at the beginning of the
                line, up to and including the file specification name. Each
                individual string should already be enclosed in quotes.
            backplane (oops.Backplane): Backplane for the observation.
            blocker (str):
                The name of one body that may be able to block or shadow
                other bodies.
            column_descs (list): A list of column descriptions.
            primary (str): Name of primary body, uppercase, e.g., "SATURN".
            target (str, optional): Optionally, the target name to write into the record.
            name_length (int, optional):
                The character width of a column to contain body names.
                If zero (which is the default), then no name is
                written into the record.
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

        Returns:
            NamedTuple (rows (list), overrides (list)):
                rows      (list): Strings comprising the resulting rows.
                overrides (list): Dicts of column entries to override in label. One dict for 
                                  each column, not including prefix columns.
        """
        if tiles is None:
            tiles = []

        # Handle option for multiple tile sets
        if isinstance(tiles, tuple):
            rows = []
            overrides = []
            local_index = start_index
            for tile in tiles:
                new_rows, new_overrides = self._prep_row(prefixes, backplane, blocker, column_descs,
                                            primary, target, name_length,
                                            tile, tiling_min, ignore_shadows,
                                            local_index, allow_zero_rows=True)
                rows += new_rows
                overrides += new_overrides
                local_index += len(tile) - 1

            if rows or allow_zero_rows:
                return (rows, overrides)

            return self._prep_row(prefixes, backplane, blocker, column_descs,
                                    primary, target, name_length,
                                    [], tiling_min, ignore_shadows,
                                    start_index, allow_zero_rows=False)

        # Handle a single set of tiles
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
        excluded_mask_dict = {}
        if self.pointing_available and not no_mask:
            for column_desc in column_descs:
                event_key = column_desc[0]
                mask_desc = column_desc[1]
                mask_target = event_key[1]

                key = (mask_target,) + mask_desc
                if key in excluded_mask_dict:
                    continue
                
                excluded_mask_dict[key] = \
                    Record._construct_excluded_mask(
                                backplane, mask_target, primary, mask_desc,
                                blocker=blocker, ignore_shadows=ignore_shadows)

        # Interpret the subregion list
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
                    Record._append_body_prefix(prefix_columns, self._get_system(target), name_length)
                    Record._append_body_prefix(prefix_columns, target, name_length)
                else:
                    Record._append_body_prefix(prefix_columns, primary, name_length)

            # Insert the subregion index
            if subregion_masks:
                prefix_columns.append('%2d' % (indx + start_index - 1))

            # Append the backplane columns
            data_columns = []
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
                    if self.pointing_available:
                        values = backplane.evaluate(event_key)
                    else:
                        values = oops.Scalar(0., True)
                        null_flag = True

                # Make a shallow copy and apply the new masks
                if excluded_mask_dict != {}:
                    target = event_key[1]
                    excluded = excluded_mask_dict[(target,) + mask_desc]
                    values = values.mask_where(excluded)
                    if len(subregion_masks) > 1:
                        values = values.mask_where(subregion_masks[indx])
                    elif len(subregion_masks) == 1:
                        values = values.mask_where(subregion_masks[0])

                if not np.all(values.mask):
                    nothing_found = False

                # Save the column using the specified format
                if len(column_desc) > 2:
                    format = ALT_FORMAT_DICT[(event_key[0], column_desc[2])]
                else:
                    format = FORMAT_DICT[event_key[0]]

                (_,_,_,_,_, null_value, valid_minimum, valid_maximum, _, _) = format
                if null_flag:
                    if isinstance(null_value, str):
                        values = null_value
                    else:
                        values = oops.Scalar(null_value, False)
                data_columns.append(self._formatted_column(values, format))

            # Save label overrides for this row
            override = {'NULL_VALUE': null_value,
                        'VALID_MINIMUM': valid_minimum,
                        'VALID_MAXIMUM': valid_maximum, 
                        }

            # Save the row if it was completed
            if len(data_columns) < len(column_descs):
                continue  # hopeless error
            if nothing_found and (indx > 0 or allow_zero_rows):
                continue
            rows.append(prefix_columns + data_columns)
            overrides.append(override)

        # Return something if we can
        if rows or allow_zero_rows:
            return (rows, overrides)

        return self._prep_row(prefixes, backplane, blocker, column_descs,
                              primary, target, name_length,
                              [], 0, ignore_shadows, start_index,
                              allow_zero_rows=False)

    #===========================================================================
    @staticmethod
    def _append_body_prefix(prefix_columns, body, length):
        """Append a body name to the column prefixes.

        Args:
            prefix_columns (list):
                A list of the strings to appear at the beginning of the
                row, up to and including the file specification name. Each
                individual string should already be enclosed in quotes.
            body (str): Body name to append.
            length (int, optional):
                The character width of a column to contain body names.

        Returns:
            None.
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

    #===========================================================================
    @staticmethod
    def _construct_excluded_mask(backplane, target, primary, mask_desc, *,
                                 blocker=None, ignore_shadows=True):
        """Return a mask using the specified target, maskers and shadowers to
        indicate excluded pixels.

        Args:
            backplane (oops.Backplne): The backplane defining the target surface.
            target (str): The name of the target surface.
            primary (str): Name of primary, e.g., "SATURN".
            mask_desc (masker, shadower, face), where:
                Masker      a string identifying what surfaces can obscure the
                target. It is a concatenation of:
                "P" to let the planet obscure the target;
                "R" to let the rings obscure the target;
                "M" to let the blocker body obscure the target.
                shadower    a string identifying what surfaces can shadow the
                target. It is a string containing:
                "P" to let the planet shadow the target;
                "R" to let the rings shadow the target;
                "M" to let the blocker body shadow the target.
                face        a string identifying which face(s) of the surface to
                include:
                "D" to include only the day side of the target;
                "N" to include only the night side of the target;
                ""  to include both faces of the target.
            blocker (str, optional):
                Optionally, the name of the body to use for any "M"
                codes that appear in the mask_desc.
            ignore_shadows (bool, optional):
                True to ignore any shadower or face constraints; default
                is False.

        Returns:
            numpy.array: Boolean bitmask containing the mask.
        """

        # Do not let a body block itself
        if target == blocker:
            blocker = None

        # Generate the new mask, with True means included
        if isinstance(target, str):
            primary_name = target.split(':')[0]
            if not oops.Body.exists(primary_name):
                return True

        (masker, shadower, face) = mask_desc

        excluded = np.zeros(backplane.shape, dtype='bool')

        # Handle maskers
        if "R" in masker and primary == "SATURN":
            excluded |= backplane.where_in_back(target, "SATURN_MAIN_RINGS").vals

        if "P" in masker:
            excluded |= backplane.where_in_back(target, primary).vals
            if primary == "PLUTO":
                excluded |= backplane.where_in_back(target, "CHARON").vals

        if "M" in masker and blocker is not None:
            excluded |= backplane.where_in_back(target, blocker).vals

        if not ignore_shadows:

            # Handle shadowers
            if "R" in shadower and primary == "SATURN":
                excluded |= backplane.where_inside_shadow(target,
                                                          "SATURN_MAIN_RINGS").vals

            if "P" in shadower:
                excluded |= backplane.where_inside_shadow(target, primary).vals
                if primary == "PLUTO":
                    excluded |= backplane.where_inside_shadow(target, "CHARON").vals

            if "M" in shadower and blocker is not None:
                excluded |= backplane.where_inside_shadow(target, blocker).vals

            # Handle face selection
            if "D" in face:
                excluded |= backplane.where_antisunward(target).vals

            if "N" in face:
                excluded |= backplane.where_sunward(target).vals

    #!!!!
    # This function does does not handle gridless backplanes properly. This
    # code fixes that, but the core problem should be fixed before this point.
        if np.any(excluded):
            return excluded
        if np.all(excluded):
            return True
        return False

    #===========================================================================
    def _circle_coverage(self, angles, null_value, flag=None):
        """Returns inferred angular coverage, accounting for the mask.

        Args:
            angles (list, np.array, or Scalar): Angles in deg.
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
                                      width=self.sampling+1, diffmin=1, alt_format=flag)

    #===========================================================================
    def _formatted_column(self, values, format):
        """Returns one formatted column (or a pair of columns) as a string.

        Args:
            values (oops.Scalar): A Scalar of values with its applied mask.
         
        Returns:
            str: Formatted column.
        """

        # Interpret the format
        (flag, number_of_values, column_width,
         standard_format, overflow_format, 
         null_value, valid_minimum, valid_maximum, _, _) = format

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
                results = self._circle_coverage(values, null_value)
    
            elif flag == "-180":
                results = self._circle_coverage(values, null_value, flag=flag)
    
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
            print(number)
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

    #===============================================================================
    def _obs_excluded(self, exceptions):
        """Use converted default bodies table to determine the primary for a given
           spacecraft clock count.

        Args:
            exceptions (list): List of regular expressions to test against the observation ID.

        Returns:
            bool: True if the observation is exluded.
        """
        if not exceptions:
            return False

        id = util.get_observation_id(self.observation)
        for exception in exceptions:
            # check for config function
            if exception.isidentifier():
                fn = getattr(config, exception)
                return fn(self.observation)

            # If no config function, treat as regex
            if re.match(exception, id):
                return True

        return False

    #===============================================================================
    def _get_primary(self, table, sclk):
        """Use converted default bodies table to determine the primary for a given
           spacecraft clock count.

        Args:
            table (list):
                Converted default bodies table containing sclk ticks instead of strings.
            sclk (str): Spacecraft clock string corresponding to the observation time.

        Returns:
            NamedTuple (primary (str), secondaries (list), selections (list), 
                        additions (list)):
                primary: Name of the primary corresponding to the given SCLK value.
                secondaries:
                    Names of any secondaries.
                selections:
                    Names of any selected bodies.
        """
        fail = ('', [], [], [])
        sclk_ticks = util.sclk_to_ticks(sclk, config.SC)
        for row in table:
            if self._obs_excluded(row[1]):
                return fail
            sclks = row[0]
            if sclk_ticks >= sclks[0] and sclk_ticks <= sclks[1]:
                return (row[2], row[3], row[4], row[5])
        return fail


################################################################################
# InventoryTable class
################################################################################
"""Class describing an inventory geometry table.
"""
class InventoryTable(com.Table):
    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for an InventoryTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path,
                         qualifier='inventory',
                         suffix="_inventory.csv",
                         use_global_template=True,
                         level=None, **kwargs)

    #===========================================================================
    def add(self, record):
        """Add an Inventory row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        line = ",".join(record.prefixes) + ',"' + ",".join(record.inventory) + '"'
        self.rows += [line]


################################################################################
# SkyTable class
################################################################################
"""Class describing a sky geometry table.
"""
class SkyTable(com.Table):
    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a SkyTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='sky', **kwargs)

    #===============================================================================
    def add(self, record):
        """Add a Sky row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        self.rows += record.add(self.qualifier, no_body=True)


################################################################################
# SunTable class
################################################################################
"""Class describing a sun geometry table.
"""
class SunTable(com.Table):
    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a SunTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='sun', **kwargs)

    #===========================================================================
    def add(self, record):
        """Add a Sun row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        self.rows += record.add(self.qualifier)


################################################################################
# RingTable class
################################################################################
"""Class describing a ring geometry table.
"""
class RingTable(com.Table):
    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a RingTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='ring', **kwargs)

    #===========================================================================
    def add(self, record):
        """Add a Ring row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """

        # Add record
        if record.primary:
            if record.rings_present:
                self.rows += record.add(self.qualifier, name=record.primary)

#        # Add other rings
#        for name in record.bodies
#           if record.rings_present:
#               self.rows += record.add(self.qualifier, name=name,
#                                       target=name+'-ring', no_mask=True


################################################################################
# BodyTable class
################################################################################
"""Class describing a body geometry table.
"""
class BodyTable(com.Table):
    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a BodyTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='body', **kwargs)

    #===========================================================================
    def add(self, record):
        """Add a Body row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        for name in record.bodies:
            self.rows += record.add(self.qualifier, name=name, target=name)


################################################################################
# Suite class
################################################################################
class Suite(object):
    """Class describing the suite of geometry tables for a single volume.
    """

    #===========================================================================
    def __init__(self, input_dir, output_dir, template_path, metadata_dir=None,
                       selection='', glob=None, index_glob=None, first=None, sampling=8):
        """Constructor for a geometry Suite object.

        Args:
            input_dir (str, Path, or FCPath): Directory containing the volume.
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
            selection (str, optional):
                A string containing...
                "S" to generate summary files;
                "D" to generate detailed files.
            glob (str, optional): Glob pattern for data files.
            index_glob (str, optional): Glob pattern for index files.
            first (bool, optional):
                If given, at most this many files are processed in each volume.
            sampling (int, optional): Pixel sampling density.
        """
        # Save inputs
        self.input_dir = FCPath(input_dir)
        self.output_dir = FCPath(output_dir)
        self.metadata_dir = FCPath(metadata_dir)
        self.template_path = FCPath(template_path)
        self.glob = glob
        self.index_glob = index_glob
        self.first = first
        self.sampling = sampling

        # Determine processing levels
        self.levels = []
        for sel in selection:
            if sel == 'S':
                self.levels += ['summary']
            if sel == 'D':
                self.levels += ['detailed']

        # Check for supplemental index
        index_filenames = list(self.metadata_dir.glob(self.index_glob))
        if len(index_filenames) == 0:
            return
        if len(index_filenames) > 1:
            raise RuntimeError('Mulitple index files found in %s.' % self.input_dir)

        index_filename = index_filenames[0]
        ext = index_filename.suffix
        self.volume_id = config.get_volume_id(self.input_dir)
        supplemental_index_name = util.get_index_name(self.input_dir,
                                                      self.volume_id, 'supplemental')
        supplemental_index_filename = \
            self.input_dir.joinpath(supplemental_index_name+ext)

        # Initialize the logger
        com.init_logger(input_dir, 'geometry')
        logger = com.get_logger()

        logger.info('New geometry index for %s.' % self.volume_id)

        # Get observations
        try:
            self.observations = config.from_index(index_filename,
                                                  supplemental_index_filename)
        except FileNotFoundError:
            logger.error(traceback.format_exc())

        # Initialize data tables
        for level in self.levels:
            self.add_tables(output_dir, level)

        # Initialize meshgrids
        self.meshgrids = config.meshgrids(sampling)

    #===========================================================================
    @staticmethod
    def get_override(record, qualifier, name=None):
        """Buld a dicstionary of column overrides.

        Args:
            record (Record): Any Record.
            qualifier: 'sky', 'sun', 'ring', or 'body'.
            name (str, optional): Name identifying a specific column description.

        Returns:
            list: Dict containing override names and values for each column.
        """

        column_descs = record.dicts[qualifier]
        if name:
            column_descs = column_descs[name]

        overrides = []
        for column_desc in column_descs:
            # Get format for this column
            event_key = column_desc[0]
            if len(column_desc) > 2:
                format = ALT_FORMAT_DICT[(event_key[0], column_desc[2])]
            else:
                format = FORMAT_DICT[event_key[0]]

            # Save label overrides for this column
            (_,_,_,_,_, null_value, valid_minimum, valid_maximum, _, _) = format
            override = {'NULL_VALUE':    null_value,
                        'VALID_MINIMUM': valid_minimum,
                        'VALID_MAXIMUM': valid_maximum, 
                       }
            overrides.append(override)

        return overrides

    #===========================================================================
    @staticmethod
    def get_overrides(record):
        """Buld a dicstionary of column overrides.

        Args:
            record (Record): Any Record.

        Returns:
            list: Dicts containing over names and values for each column.
        """
        overrides = {}

        overrides['sky'] = Suite.get_override(record, 'sky')
#        overrides['sun'] = Suite.get_override(record, 'sun')
        overrides['ring'] = Suite.get_override(record, 'ring', name=record.primary)
        overrides['body'] = Suite.get_override(record, 'body', name=record.primary)

        return overrides

    #===========================================================================
    def add_tables(self, output_dir, level):
        """Add a set of tables.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
           level (str): 'summary' or'detailed''.

        Returns:
            None.
        """
        self.tables = [
            InventoryTable(output_dir, self.template_path, volume_id=self.volume_id),
            SkyTable(output_dir, self.template_path, volume_id=self.volume_id, level=level),
#            SunTable(output_dir, self.template_path, volume_id=self.volume_id, level=level),
            RingTable(output_dir, self.template_path, volume_id=self.volume_id, level=level),
            BodyTable(output_dir, self.template_path, volume_id=self.volume_id, level=level)
            ]

    #===========================================================================
    def make_records(self, index):
        """Add a record for each processing level.

        Args:
           index (int): Row index.

        Returns:
            list: One record for each processing level.
        """
        records = []
        for level in self.levels:
            records.append(
                Record(self.observations[index], 
                       self.volume_id, 
                       self.meshgrids, 
                       self.sampling, 
                       level))
        return records

    #===========================================================================
    def add(self, records):
        """Add a row to all tables.

        Args:
            records (list):
                Records describing the rows to add, one for each processing level.

        Returns:
            None.
        """
        for table in self.tables:
            for record in records:
                if (record.level == table.level) | (table.level is None):
                    table.add(record)

    #===========================================================================
    def write(self, labels_only=False):
        """Write all tables and their labels.

        Args:
            labels_only (bool):
                If True, labels are generated for any existing geometry tables.

        Returns:
            None
        """
        for table in self.tables:
            table.write(labels_only=labels_only)

    #===========================================================================
    def create(self, labels_only=False, pattern=None):
        """Process the volume and write a suite of geometry files.

        Args:
            labels_only (bool):
                If True, labels are generated for any existing geometry tables.
            pattern (str): Glob pattern for sub-selecting files to process.

        Returns:
            None
        """
        logger = com.get_logger()

        if not hasattr(self, 'observations'):
            return

        # Loop through the observations...
        nobs = len(self.observations)
        count = 0
        if not labels_only:
            for i in range(nobs):
                name = self.observations[i].basename

                # Make any sub selection
                if pattern and fnmatch.filter([self.observations[i].filespec], pattern) == []:
                    logger.warning("Skipping %s; pattern mismatch.", name)
                    continue

                # Match the glob patternname
                match = fnmatch.filter([name], self.glob)
                if match == []:
                    logger.warning("Skipping %s; glob mismatch.", name)
                    continue
                file = match[0]

                # Abort if count exceeds a specified limit
                if self.first and count >= self.first:
                    continue

                # Print a log of progress
                logger.info("%s  %s %4d/%4d" % (self.volume_id, file, i+1, nobs))

                # Construct the record for this observation
                records = self.make_records(i)
#                   # Build overrides dict
#                   if count == 0:
#                       overrides = Suite.get_overrides(records[0])
                # Update the tables
                self.add(records)
                count += 1

        # Run post-processor
#        self.post()

        # Write tables and make labels
        self.write(labels_only=labels_only)

        # Clean up
        config.cleanup()
        logger.close()


################################################################################
# external functions
################################################################################

#===============================================================================
def get_args(host=None, selection=None, exclude=None, sampling=8):
    """Argument parser for geometric metadata.

    Args:
        host (str): Host name, e.g. 'GOISS'.
        selection (str, optional):
            A string containing...
            "S" to generate summary files;
            "D" to generate detailed files.
        exclude (list, optional): List of volumes to exclude.
        sampling (int, optional): Pixel sampling density.

     Returns:
        argparser.ArgumentParser :
            Parser containing the argument specifications.
    """

    # Get common args
    parser = com.get_common_args(host=host, volume_arg=None)

    # Add geometry args
    gr = parser.add_argument_group('Geometry Arguments')
    gr.add_argument('--selection', type=str, metavar='selection',
                    default=selection,
                    help='''A string containing:
                             "S" to generate summary files;
                             "D" to generate detailed files.''')
    gr.add_argument('--exclude', '-e', nargs='*', type=str, metavar='exclude',
                    default=exclude,
                    help='''List of volumes to exclude.''')
    gr.add_argument('--new_only', '-n', nargs='*', type=str, metavar='new_only',
                    default=False,
                    help='''Only volumes that contain no output files are processed.''')
    gr.add_argument('--first', '-f', type=int, metavar='first',
                    help='''If given, at most this many input files are processed
                            in each volume.''')
    gr.add_argument('--sampling', '-s', type=int, metavar='sampling',
                    default=sampling,
                    help='''Pixel sampling density.''')

    # Return parser
    return parser

#===============================================================================
def process_tables(template_name,
                   volumes=None,
                   selection=None,
                   exclude=None,
                   sampling=8,
                   glob=None,
                   index_glob=None,
                   args=None,
                   task_file=None, 
                   task_list_only=False):
    """Create geometry tables for a collection of volumes.

    Args:
        template_name (str): Name of index template.
        volumes (list, optional): List of volume ids to process. Overrides args.volumes.
        selection (str, optional):
            A string containing...
            "S" to generate summary files;
            "D" to generate detailed files.
        exclude (list, optional): List of volumes to exclude.
        sampling (int, optional): Pixel sampling density.
        glob (str, optional): Glob pattern for data files.
        index_glob (str, optional): Glob pattern for index files.
        args (argparse.Namespace): Parsed arguments.
        task_file (str, optional): 
            Name of tasks file. This file is overwritten. If not given, tasks are provided 
            via the task_source generator.
        task_list_only (bool, optional):
            If True, a task list is created and no processing is performed. If task_file is
            given, then the task list is written to that file. Otherwise, the task list is
            accessed via the task_source generator. 
    """

    # Parse arguments
    host, _index_type, template_dir = util.parse_template_name(template_name)
    template_path = template_dir / FCPath(template_name).with_suffix('.lbl')
    if args is None:
        parser = get_args(host=host, selection=selection, exclude=exclude, sampling=sampling)
        args = parser.parse_args()

    metadata_tree = FCPath(args.metadata_tree)
    output_tree = FCPath(args.output_tree)
    new_only = args.new_only is not False
    labels_only = args.labels is not False

    if volumes is None:
        volumes = args.volumes

    if volumes:
        new_only = False

    # Build volume glob
    vol_glob = util.get_volume_glob(output_tree.name)

    # Walk the volume tree, making indexes for each found volume
    for root, dirs, _files in output_tree.walk():
        # __skip directory will not be scanned, so it's safe for test results
        if '__skip' in root.as_posix():
            continue

        # Sort directories for progress monitoring
        dirs.sort()
        root = FCPath(root)

        # Determine notional collection and volume
        parts = root.parts
        coll = parts[-2]
        vol = parts[-1]

        # Proceed only if this root is a volume
        if fnmatch.filter([vol], vol_glob):
            if not volumes or vol in volumes:

                # Set up input and output directories
                indir = root
                outdir = util.select_dir(output_tree, coll, vol)
                metadata_dir = util.select_dir(metadata_tree, coll, vol)

                # Do not continue if this volume is excluded
                skip = False
                if exclude is not None:
                    for item in exclude:
                        if item in indir.parts:
                            skip = True
                if skip:
                    continue

                # Check whether this volume has already been processed
                if new_only and (list(outdir.glob('*_inventory.csv')) != []):
                    continue

                # Update the task file...
                if task_list_only:
                    com.add_task(vol, 'geometry')
                    
                # ... or process this volume
                else:
                    suite = Suite(indir, outdir, template_path, metadata_dir,
                                  selection=args.selection, glob=glob, index_glob=index_glob, 
                                  first=args.first, sampling=args.sampling)
                    suite.create(labels_only=labels_only, pattern=args.pattern)

    # Write the task file
    if task_list_only:
        com.write_task_file(task_file)

################################################################################
