################################################################################
# COLUMNS_SUN.py: Column definitions for sun geometry tables
################################################################################

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
SUN_COLUMNS = [
    (("latitude",               "SUN", "centric"),           ("",  "",  "")),
    (("latitude",               "SUN", "graphic"),           ("",  "",  "")),
    (("longitude",              "SUN", "iau", "west"),       ("",  "",  "")),
#     (("longitude",              "SUN", "iau", "east"),      ("",  "",  "")),
    (("longitude",              "SUN", "obs", "west", -180), ("",  "",  ""), "-180"),
#     (("longitude",              "SUN", "obs", "east", -180), ("",  "",  ""), "-180"),
    (("finest_resolution",      "SUN"),                      ("",  "",  "")),
    (("coarsest_resolution",    "SUN"),                      ("",  "",  "")),
    (("distance",               "SUN"),                      ("",  "",  "")),
    (("event_time",             "SUN"),                      ("", "", ""))]

SUN_GRIDLESS_COLUMNS = [
    (("sub_observer_latitude",  "SUN", "centric"),           ("",   "",  "")),
    (("sub_observer_latitude",  "SUN", "graphic"),           ("",   "",  "")),
    (("sub_observer_longitude", "SUN", "iau", "west"),       ("",   "",  "")),
#     (("sub_observer_longitude", "SUN", "iau", "east"),      ("",   "",  "")),
    (("center_resolution",      "SUN", "u"),                 ("",   "",  "")),
    (("center_distance",        "SUN", "obs"),               ("",   "",  "")),
    (("radius_in_pixels",       "SUN"),                      ("",   "",  "")),
    (("center_coordinate",      "SUN", "x"),                 ("",   "",  "")),
    (("center_coordinate",      "SUN", "y"),                 ("",   "",  ""))]

SUN_SUMMARY_COLUMNS  = SUN_COLUMNS + SUN_GRIDLESS_COLUMNS
SUN_DETAILED_COLUMNS = SUN_COLUMNS
################################################################################
