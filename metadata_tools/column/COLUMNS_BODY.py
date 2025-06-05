################################################################################
# COLUMNS_BODY.py: Column definitions for body geometry tables
################################################################################
import oops

################################################################################
# *COLUMN description tuples are
#
#   (backplane_key, (masker, shadower, face), alt_format)
#
# where...
#
#   backplane_key   tuple passed to Backplane.evaluate().
#
#   masker          a string indicating which bodies obscure the surface. It is
#                   constructed by concatenating any of these characters:
#                       "P" = let the planet mask the surface;
#                       "R" = let the rings mask the surface;
#                       "M" = let the moon mask the surface.
#
#   shadower        a string indicating which bodies shadow the surface. It is
#                   constructed by concatenating any of these characters:
#                       "P" = let the planet shadow the surface;
#                       "R" = let the rings shadow the surface;
#                       "M" = let the moon shadow the surface.
#
#   face            a string indicating which face of the surface to include:
#                       "D" = include only the day side of the body;
#                       "N" = include only the night side of the body;
#                       ""  = include both faces of the body.
#
#   alt_format      if present, this is an extra tag used to identify the output
#                   format of the column.
#                       "-180" = use the range (-180,180) instead of (0,360).
#
################################################################################
BODY_COLUMNS = [
    (("latitude",               defs.BODYX, "centric"),         ("RM", "R",  "D")),
    (("latitude",               defs.BODYX, "graphic"),         ("RM", "R",  "D")),
    (("longitude",              defs.BODYX, "iau", "west"),     ("RM", "R",  "D")),
#    (("longitude",              defs.BODYX, "iau", "east"),     ("RM", "R",  "D")),
    (("longitude",              defs.BODYX, "sha", "east"),     ("RM", "R",  "")),
    (("longitude",              defs.BODYX, "obs", "west"),
                                                            ("RM", "R",  "D"), "-180"),
#    (("longitude",              defs.BODYX, "obs", "east"),
#                                                            ("RM", "R",  "D"), "-180"),
    (("finest_resolution",      defs.BODYX),                    ("RM", "R",  "D")),
    (("coarsest_resolution",    defs.BODYX),                    ("RM", "R",  "D")),
    (("distance",               defs.BODYX),                    ("RM", "",   "")),
#    (("phase_angle",            defs.BODYX),                    ("RM", "",   "D")),
    (("phase_angle",            defs.BODYX),                    ("RM", "",   "")),
    (("incidence_angle",        defs.BODYX),                    ("RM", "",   "")),
    (("emission_angle",         defs.BODYX),                    ("RM", "",   "")),
    (("limb_altitude",          defs.BODYX, -0.01, 1000, True), ("",   "",  "")),
    (("limb_clock_angle",       defs.BODYX),                    ("",   "",  "")),
    (("event_time",             defs.BODYX),                    ("RM", "", ""))]

BODY_GRIDLESS_COLUMNS = [
    (("sub_solar_latitude",     defs.BODYX, "centric"),         ("",   "",  "")),
    (("sub_solar_latitude",     defs.BODYX, "graphic"),         ("",   "",  "")),
    (("sub_observer_latitude",  defs.BODYX, "centric"),         ("",   "",  "")),
    (("sub_observer_latitude",  defs.BODYX, "graphic"),         ("",   "",  "")),
    (("sub_solar_longitude",    defs.BODYX, "iau", "west"),     ("",   "",  "")),
#    (("sub_solar_longitude",    defs.BODYX, "iau", "east"),     ("",   "",  "")),
    (("sub_observer_longitude", defs.BODYX, "iau", "west"),     ("",   "",  "")),
#    (("sub_observer_longitude", defs.BODYX, "iau", "east"),     ("",   "",  "")),
    (("center_resolution",      defs.BODYX, "u"),               ("",   "",  "")),
    (("center_distance",        defs.BODYX, "obs"),             ("",   "",  "")),
    (("center_phase_angle",     defs.BODYX),                    ("",   "",  "")),
    (("body_diameter_in_pixels",defs.BODYX),                    ("",   "",  "")),
    (("pole_clock_angle",       defs.BODYX),                    ("",   "",  "")),
    (("pole_position_angle",    defs.BODYX),                    ("",   "",  "")),
    (("center_coordinate",      defs.BODYX, "u"),               ("",   "",  "")),
    (("center_coordinate",      defs.BODYX, "v"),               ("",   "",  ""))]

# Assemble the column lists for each type of file for the moons and planet

BODY_SUMMARY_COLUMNS  = BODY_COLUMNS + BODY_GRIDLESS_COLUMNS
BODY_DETAILED_COLUMNS = BODY_COLUMNS

BODY_SUMMARY_DICT = {}
BODY_DETAILED_DICT = {}
for body in BODIES:
    BODY_SUMMARY_DICT.update(util.replacement_dict(BODY_SUMMARY_COLUMNS,
                                                         defs.BODYX, [body]))
    BODY_DETAILED_DICT.update(util.replacement_dict(BODY_DETAILED_COLUMNS,
                                                         defs.BODYX, [body]))
################################################################################
# Define the tiling for detailed listings
#
# The first item in the list defines a region to test for a suitable pixel
# count. The remaining items define a sequence of tiles to use in a
# detailed tabulation.
################################################################################
BODY_TILES = {}
for body in defs.BODY_NAMES:
    BODY_TILES[body] = [
        ("where_all", ("where_in_front", defs.BODYX, body),  # mask over remaining tiles
                      ("where_sunward",  defs.BODYX)),
        ("where_below",   ("latitude", defs.BODYX), -70. * oops.RPD),
        ("where_between", ("latitude", defs.BODYX), -70. * oops.RPD, -50. * oops.RPD),
        ("where_between", ("latitude", defs.BODYX), -50. * oops.RPD, -30. * oops.RPD),
        ("where_between", ("latitude", defs.BODYX), -30. * oops.RPD, -10. * oops.RPD),
        ("where_between", ("latitude", defs.BODYX), -10. * oops.RPD,  10. * oops.RPD),
        ("where_between", ("latitude", defs.BODYX),  10. * oops.RPD,  30. * oops.RPD),
        ("where_between", ("latitude", defs.BODYX),  30. * oops.RPD,  50. * oops.RPD),
        ("where_between", ("latitude", defs.BODYX),  50. * oops.RPD,  70. * oops.RPD),
        ("where_above",   ("latitude", defs.BODYX),  70. * oops.RPD)
    ]

BODY_TILE_DICT = {}

for body in defs.BODY_NAMES:
    BODY_TILE_DICT[body] = {}
    BODY_TILE_DICT[body] = util.replace(BODY_TILES[body], defs.BODYX, body)
################################################################################
