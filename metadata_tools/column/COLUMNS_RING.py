################################################################################
# COLUMNS_RING.py: Column definitions for ring geometry tables
################################################################################
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
    (("center_coordinate",       defs.BODYX, "u"),                ("",   "",  "")),
    (("center_coordinate",       defs.BODYX, "v"),                ("",   "",  ""))]

# Assemble the column lists for each type of file for the rings and for Saturn
RING_SUMMARY_COLUMNS  = (RING_COLUMNS + ANSA_COLUMNS +
                         RING_GRIDLESS_COLUMNS)
RING_DETAILED_COLUMNS = RING_COLUMNS + ANSA_COLUMNS

# Create a dictionary for the columns of each planet
RING_SUMMARY_DICT = {}
RING_DETAILED_DICT = {}
for body in defs.BODY_NAMES:
    RING_SUMMARY_DICT.update(util.replacement_dict(RING_SUMMARY_COLUMNS,
                                                         defs.BODYX, [body]))
    RING_DETAILED_DICT.update(util.replacement_dict(RING_DETAILED_COLUMNS,
                                                         defs.BODYX, [body]))

################################################################################
# Define the tiling for detailed listings
#
# The first item in the list defines a region to test for a suitable pixel
# count. The remaining items define a sequence of tiles to use in a
# detailed tabulation.
################################################################################
RING_AZ = ("ring_azimuth", planet_ring, "obs")

RING_TILES = {}
for body in defs.BODY_NAMES:
    RING_TILES[body] = [
        ("where_all",                                   # mask over remaining tiles
            ("where_in_front", planet_ring, defs.BODYX),
            ("where_outside_shadow", planet_ring, defs.BODYX),
            ("where_below", ("ring_radius", planet_ring), 150000.)),
        ("where_between", RING_AZ, 0.20 * np.pi, 0.45 * np.pi),
        ("where_between", RING_AZ, 0.45 * np.pi, 0.55 * np.pi),
        ("where_between", RING_AZ, 0.55 * np.pi, 0.80 * np.pi),
        ("where_between", RING_AZ, 0.80 * np.pi, 1.20 * np.pi),
        ("where_between", RING_AZ, 1.20 * np.pi, 1.45 * np.pi),
        ("where_between", RING_AZ, 1.45 * np.pi, 1.55 * np.pi),
        ("where_between", RING_AZ, 1.55 * np.pi, 1.80 * np.pi),
        ("where_any",
            ("where_below", RING_AZ, 0.20 * np.pi),
            ("where_above", RING_AZ, 1.80 * np.pi)),
    ]

OUTER_RING_TILES = {}
for body in defs.BODY_NAMES:
    OUTER_RING_TILES[body] = [
        ("where_all",                                   # mask over remaining tiles
                ("where_in_front", planet_ring, defs.BODYX),
        ("where_above", ("ring_radius", planet_ring), 150000.)),
        ("where_between", RING_AZ, 0.20 * np.pi, 0.45 * np.pi),
        ("where_between", RING_AZ, 0.45 * np.pi, 0.55 * np.pi),
        ("where_between", RING_AZ, 0.55 * np.pi, 0.80 * np.pi),
        ("where_between", RING_AZ, 0.80 * np.pi, 1.20 * np.pi),
        ("where_between", RING_AZ, 1.20 * np.pi, 1.45 * np.pi),
        ("where_between", RING_AZ, 1.45 * np.pi, 1.55 * np.pi),
        ("where_between", RING_AZ, 1.55 * np.pi, 1.80 * np.pi),
        ("where_between", RING_AZ, 0.80 * np.pi, 1.20 * np.pi),
        ("where_any",
            ("where_below", RING_AZ, 0.20 * np.pi),
            ("where_above", RING_AZ, 1.80 * np.pi)),
    ]

RING_TILE_DICT = {}
for body in defs.BODY_NAMES:
    RING_TILE_DICT[body] = util.replace(RING_TILES[body], defs.BODYX, body)

OUTER_RING_TILE_DICT = {}
for body in defs.BODY_NAMES:
    OUTER_RING_TILE_DICT[body] = util.replace(OUTER_RING_TILES[body], defs.BODYX, body)

################################################################################
