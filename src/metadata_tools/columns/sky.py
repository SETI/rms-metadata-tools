"""Column definitions for sky geometry tables.

This module defines the backplane columns describing the inertial pointing of
each pixel on the sky (right ascension and declination) in SKY_COLUMNS.

These definitions are gathered and re-exported by ``columns/__init__.py`` and
consumed by the geometry Record/prep code, which evaluates each backplane key
and formats the result via FORMAT_DICT in the ``geometry_support`` package (defined
in its ``formats`` module).
"""

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
