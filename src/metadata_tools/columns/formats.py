"""Conversion and linking metadata for geometry columns.

This module holds the per-backplane-quantity metadata that a PDS3 label cannot
express: the unit-conversion flag applied before formatting, the overflow print
format used when a value will not fit its field, and the null-link grouping.

Everything a label *can* express now lives in the templates and is read back by
:mod:`metadata_tools.geometry_support.label_schema`: the column set and its
order, each column's NAME, its width and print format (from ``FORMAT``), its
null value, and its valid range.

This module lives under ``columns/`` rather than ``geometry_support/`` to keep
the dependency one-way: ``columns`` must never import ``geometry_support``,
because ``geometry_support.record`` imports ``columns``.
"""

# A format tuple is (flag, overflow_format, link_id, link), where...
#
#   flag = "DEG"  = convert values from radians to degrees;
#        = "360"  = convert to degrees; report cyclic coverage in the range (0,360);
#        = "-180" = convert to degrees; report cyclic coverage in the range (-180,180);
#        = "ISO"  = format TAI seconds as an ISO date-time string;
#        = "KM"   = tabulate values in km, with no unit conversion applied;
#        = ""     = do not modify value.
#
#   overflow_format is the print format substituted when a value overflows its
#   field width, or None when the column cannot overflow.
#
#   link_id is a positive integer id that can be used to link multiple columns
#   via the specified link function. All columns with the same link function and
#   link id are linked together.
#
# To add a geometry column, see "Adding a geometry column" in the developer
# guide; the label template is the starting point, not this file.

FormatTuple = tuple[str, str | None, int, str]

_FORMAT_DICT: dict[str, FormatTuple] = {
    "right_ascension"             : ('360', '%10.5f', 0, ''),
    "declination"                 : ('DEG', '%10.5f', 0, ''),
    "distance"                    : ('', '%12.5e', 0, ''),
    "center_distance"             : ('', '%12.5e', 0, ''),
    "center_coordinate"           : ('', '%12.5e', 1, 'null'),
    "radius_in_pixels"            : ('', '%12.5e', 0, ''),
    "ring_radius"                 : ('', '%12.5e', 0, ''),
    "ansa_radius"                 : ('', '%12.5e', 0, ''),
    "ansa_altitude"               : ('', '%12.5e', 0, ''),
    "resolution"                  : ('', '%10.4e', 0, ''),
    "finest_resolution"           : ('', '%10.4e', 0, ''),
    "coarsest_resolution"         : ('', '%10.4e', 0, ''),
    "ring_radial_resolution"      : ('', '%10.4e', 0, ''),
    "ansa_radial_resolution"      : ('', '%10.4e', 0, ''),
    "center_resolution"           : ('', '%10.4e', 0, ''),
    "body_diameter_in_pixels"     : ('', '%12.5e', 0, ''),
    "event_time"                  : ('ISO', '%25s', 0, ''),
    "ring_angular_resolution"     : ('DEG', '%6.3e', 0, ''),
    "longitude"                   : ('360', None, 0, ''),
    "ring_longitude"              : ('360', None, 0, ''),
    "ring_azimuth"                : ('360', None, 0, ''),
    "ansa_longitude"              : ('360', None, 0, ''),
    "sub_solar_longitude"         : ('360', None, 0, ''),
    "sub_observer_longitude"      : ('360', None, 0, ''),
    "ring_sub_solar_longitude"    : ('360', None, 0, ''),
    "ring_sub_observer_longitude" : ('360', None, 0, ''),
    "latitude"                    : ('DEG', None, 0, ''),
    "sub_solar_latitude"          : ('DEG', None, 0, ''),
    "sub_observer_latitude"       : ('DEG', None, 0, ''),
    "limb_altitude"               : ('', '%12.5e', 0, ''),
    "limb_clock_angle"            : ('360', None, 0, ''),
    "pole_clock_angle"            : ('DEG', None, 0, ''),
    "pole_position_angle"         : ('DEG', None, 0, ''),
    "phase_angle"                 : ('DEG', None, 0, ''),
    "center_phase_angle"          : ('DEG', None, 0, ''),
    "incidence_angle"             : ('DEG', None, 0, ''),
    "ring_incidence_angle"        : ('DEG', None, 0, ''),
    "ring_center_incidence_angle" : ('DEG', None, 0, ''),
    "emission_angle"              : ('DEG', None, 0, ''),
    "ring_emission_angle"         : ('DEG', None, 0, ''),
    "ring_center_emission_angle"  : ('DEG', None, 0, ''),
    "ring_elevation"              : ('DEG', None, 0, '')}
"""Conversion/overflow/link metadata for each backplane quantity."""

_ALT_FORMAT_DICT: dict[tuple[str, str], FormatTuple] = {
    ("ring_angular_resolution", "km")        : ('KM', '%10.4e', 0, ''),
    ("longitude", "-180")                    : ('-180', None, 0, ''),
    ("ring_longitude", "-180")               : ('-180', None, 0, '')}
"""Alternate entries keyed by ``(backplane quantity, alt-format tag)``."""


#===============================================================================
def resolve_format(key: str, alt: str | None = None) -> FormatTuple:
    """Return the format tuple for a backplane quantity.

    Parameters:
        key: The backplane quantity, i.e. the first element of a backplane key.
        alt: An optional alternate-format tag selecting a variant entry.

    Returns:
        The matching format tuple.

    Raises:
        KeyError: If the quantity (or the tagged variant) has no entry.
    """
    if alt is not None:
        return _ALT_FORMAT_DICT[(key, alt)]
    return _FORMAT_DICT[key]
