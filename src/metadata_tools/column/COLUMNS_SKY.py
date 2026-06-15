################################################################################
# COLUMNS_SKY.py: Column definitions for sky geometry tables
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
SKY_COLUMNS = [
    (("right_ascension",        ()),                        ("",  "",  "")),
    (("declination",            ()),                        ("",  "",  ""))]

################################################################################
# Define the tiling for detailed listings
#
# The first item in the list defines a region to test for a suitable pixel
# count. The remaining items define a sequence of tiles to use in a
# detailed tabulation.
################################################################################
###TODO: not tested...
SKY_TILES = [
    ("where_all", ""),                      # mask over remaining tiles
    ("where_below",   ("declination", ""), -70. * oops.RPD),
    ("where_between", ("declination", ""), -70. * oops.RPD, -50. * oops.RPD),
    ("where_between", ("declination", ""), -50. * oops.RPD, -30. * oops.RPD),
    ("where_between", ("declination", ""), -30. * oops.RPD, -10. * oops.RPD),
    ("where_between", ("declination", ""), -10. * oops.RPD,  10. * oops.RPD),
    ("where_between", ("declination", ""),  10. * oops.RPD,  30. * oops.RPD),
    ("where_between", ("declination", ""),  30. * oops.RPD,  50. * oops.RPD),
    ("where_between", ("declination", ""),  50. * oops.RPD,  70. * oops.RPD),
    ("where_above",   ("declination", ""),  70. * oops.RPD)
]

################################################################################
