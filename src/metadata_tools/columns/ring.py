"""Column definitions for ring geometry tables.

This module defines the backplane columns describing ring-plane and ansa
geometry: per-pixel ring quantities (RING_COLUMNS), ansa quantities
(ANSA_COLUMNS), gridless whole-ring quantities (RING_GRIDLESS_COLUMNS), and the
summary column list assembled from them. It also builds the per-body
replacement dictionary.

These definitions are gathered and re-exported by ``columns/__init__.py`` and
consumed by the geometry Record/prep code, which evaluates each backplane key
and formats the result via FORMAT_DICT in the ``geometry_support`` package (defined
in its ``formats`` module).
"""

import metadata_tools.defs as defs
import metadata_tools.util as util

planet_ring = defs.BODYX + ":RING"
planet_ansa = defs.BODYX + ":ANSA"

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
RING_COLUMNS = [
    (("ring_radius",             planet_ring),               ("PM", "P", "")),
    (("resolution",              planet_ring, "v"),          ("PM", "P", "")),
    (("ring_radial_resolution",  planet_ring),               ("PM", "P", "")),
    (("ring_angular_resolution", planet_ring),               ("PM", "P", "")),
    (("ring_angular_resolution", planet_ring, "km"),         ("PM", "P", ""), "km"),
    (("distance",                planet_ring),               ("PM", "P", "")),
    (("ring_longitude",          planet_ring, "aries"),      ("PM", "P", "")),
    (("ring_longitude",          planet_ring, "node"),       ("PM", "P", "")),
    (("ring_longitude",          planet_ring, "sha"),        ("PM", "",  "")),
    (("ring_longitude",          planet_ring, "obs"),  ("PM", "P", ""), "-180"),
    (("ring_azimuth",            planet_ring, "obs"),        ("PM", "P", "")),
    (("phase_angle",             planet_ring),               ("PM", "P", "")),
    (("ring_incidence_angle",    planet_ring),               ("PM", "P", "")),
    (("ring_incidence_angle",    planet_ring, "prograde"),   ("PM", "P", "")),
    (("ring_emission_angle",     planet_ring),               ("PM", "P", "")),
    (("ring_emission_angle",     planet_ring, "prograde"),   ("PM", "P", "")),
    (("ring_elevation",          planet_ring, "sun"),        ("PM", "P", "")),
    (("ring_elevation",          planet_ring, "obs"),        ("PM", "P", "")),
    (("event_time",              planet_ring),               ("PM", "P", ""))]
#    (("ring_elevation",          planet_ring, "sun", "prograde", False), ("PM", "P", "")),
#    (("ring_elevation",          planet_ring, "obs", "prograde", False), ("PM", "P", ""))]

ANSA_COLUMNS = [
    (("ansa_radius",             planet_ansa),               ("PM", "P", "")),
    (("ansa_altitude",           planet_ansa),               ("PM", "P", "")),
    (("ansa_radial_resolution",  planet_ansa),               ("PM", "P", "")),
    (("distance",                planet_ansa),               ("PM", "P", "")),
    (("ansa_longitude",          planet_ansa, "aries"),      ("PM", "P", "")),
    (("ansa_longitude",          planet_ansa, "node"),       ("PM", "P", "")),
    (("ansa_longitude",          planet_ansa, "sha"),        ("PM", "P", ""))]
#    (("ansa_longitude",          planet_ansa, "obs"),        ("PM", "P", ""))]

RING_GRIDLESS_COLUMNS = [
    (("center_distance",         planet_ring, "obs"),        ("",   "",  "")),
    (("ring_sub_solar_longitude",
                                 planet_ring, "aries"),      ("",   "",  "")),
    (("ring_sub_solar_longitude",
                                 planet_ring, "node"),       ("",   "",  "")),
    (("ring_sub_observer_longitude",
                                 planet_ring, "aries"),      ("",   "",  "")),
    (("ring_sub_observer_longitude",
                                 planet_ring, "node"),       ("",   "",  "")),
    (("center_phase_angle",      planet_ring),               ("",   "",  "")),
    (("ring_center_incidence_angle",
                                 planet_ring),               ("",   "",  "")),
    (("ring_center_incidence_angle",
                                 planet_ring, "prograde"),   ("",   "",  "")),
    (("ring_center_emission_angle",
                                 planet_ring),               ("",   "",  "")),
    (("ring_center_emission_angle",
                                 planet_ring, "prograde"),   ("",   "",  "")),
    (("sub_solar_latitude",      planet_ring),               ("",   "",  "")),
    (("sub_observer_latitude",   planet_ring),               ("",   "",  "")),
    (("body_diameter_in_pixels", planet_ring,
                            util.replacement_fn("defs.RING_SYSTEM_RADII", defs.BODYX)),
                                                            ("",   "",  "")),
    (("pole_clock_angle",       defs.BODYX),                    ("",   "",  "")),
    (("pole_position_angle",    defs.BODYX),                    ("",   "",  "")),
    (("center_coordinate",       defs.BODYX, "u"),                ("",   "",  "")),
    (("center_coordinate",       defs.BODYX, "v"),                ("",   "",  ""))]

# Assemble the column list for the rings and for Saturn
RING_SUMMARY_COLUMNS  = (RING_COLUMNS + ANSA_COLUMNS +
                         RING_GRIDLESS_COLUMNS)

# Create a dictionary for the columns of each planet
RING_SUMMARY_DICT = {}
for body in defs.BODY_NAMES:
    RING_SUMMARY_DICT.update(util.replacement_dict(RING_SUMMARY_COLUMNS,
                                                         defs.BODYX, [body]))

################################################################################
