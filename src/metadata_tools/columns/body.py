"""Column definitions for body geometry tables.

This module defines the backplane columns describing the geometry of a body's
surface (moons and the planet): per-pixel quantities (BODY_COLUMNS), gridless
whole-body quantities (BODY_GRIDLESS_COLUMNS), and the summary column list
assembled from them. It also builds the per-body replacement dictionary.

These definitions are gathered and re-exported by ``columns/__init__.py`` and
consumed by the geometry Record/prep code, which evaluates each backplane key
and formats the result via FORMAT_DICT in the ``geometry_support`` package (defined
in its ``formats`` module).
"""
from typing import Any

import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.bodies import get_bodies_registry

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
    (("limb_altitude",          defs.BODYX, -0.01, 3, True),    ("",   "",  "")),
    (("limb_clock_angle",       ("limb_altitude", defs.BODYX, -0.01, 3, True)), ("",   "",  "")),
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

_BODY_SUMMARY_DICT: dict[str, Any] | None = None


def get_body_summary_dict() -> dict[str, Any]:
    """Return the per-body summary column replacement dict, building it on first call."""
    global _BODY_SUMMARY_DICT
    if _BODY_SUMMARY_DICT is None:
        summary: dict[str, Any] = {}
        for body in get_bodies_registry():
            summary.update(util.replacement_dict(BODY_SUMMARY_COLUMNS, defs.BODYX, [body]))
        _BODY_SUMMARY_DICT = summary
    return _BODY_SUMMARY_DICT
################################################################################
