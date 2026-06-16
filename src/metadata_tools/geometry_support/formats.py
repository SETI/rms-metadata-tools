################################################################################
# geometry_support/formats.py - Geometry column format dictionaries.
################################################################################
import geometry_config as config

import metadata_tools.util as util

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
#   1. Add a column definition to a column definition file, e.g. columns/body.py.
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
    "center_coordinate"         : ("",    1, 12, "%12.3f", "%12.5e", -99999, -10000, 10000, 1,
                                   'null'),
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
