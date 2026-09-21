"""Column computation catalog for body geometry tables.

This module names every body geometry column this package knows how to compute
and says how: the backplane key describing a body's surface (moons and the
planet), the bodies that mask it, and the unit conversion applied to the result.

Whether a column is actually produced -- and in what order, with what width,
null value, and valid range -- is decided by the host's label template, not
here. An entry no template names is simply unused. See
:mod:`metadata_tools.columns.catalog`.
"""
import metadata_tools.defs as defs
from metadata_tools.columns.catalog import ColumnSpec, minmax, single

BODY_CATALOG: tuple[ColumnSpec, ...] = (
    minmax('PLANETOCENTRIC_LATITUDE', ('latitude', defs.BODYX, 'centric'),
           ('RM', 'R', 'D')),
    minmax('PLANETOGRAPHIC_LATITUDE', ('latitude', defs.BODYX, 'graphic'),
           ('RM', 'R', 'D')),
    minmax('IAU_LONGITUDE', ('longitude', defs.BODYX, 'iau', 'west'),
           ('RM', 'R', 'D')),
    minmax('LOCAL_HOUR_ANGLE', ('longitude', defs.BODYX, 'sha', 'east'),
           ('RM', 'R', '')),
    minmax('LONGITUDE_WRT_OBSERVER', ('longitude', defs.BODYX, 'obs', 'west'),
           ('RM', 'R', 'D'), alt='-180'),
    minmax('FINEST_SURFACE_RESOLUTION', ('finest_resolution', defs.BODYX),
           ('RM', 'R', 'D')),
    minmax('COARSEST_SURFACE_RESOLUTION', ('coarsest_resolution', defs.BODYX),
           ('RM', 'R', 'D')),
    minmax('SURFACE_DISTANCE', ('distance', defs.BODYX),
           ('RM', '', '')),
    minmax('PHASE_ANGLE', ('phase_angle', defs.BODYX),
           ('RM', '', '')),
    minmax('INCIDENCE_ANGLE', ('incidence_angle', defs.BODYX),
           ('RM', '', '')),
    minmax('EMISSION_ANGLE', ('emission_angle', defs.BODYX),
           ('RM', '', '')),
    minmax('LIMB_ALTITUDE', ('limb_altitude', defs.BODYX, -0.01, 3, True),
           ('', '', '')),
    minmax('LIMB_CLOCK_ANGLE', ('limb_clock_angle', ('limb_altitude', defs.BODYX, -0.01, 3, True)),
           ('', '', '')),
    minmax('SURFACE_INTERCEPT_TIME', ('event_time', defs.BODYX),
           ('RM', '', '')),
    minmax('PLANETOCENTRIC_SUB_SOLAR_LATITUDE', ('sub_solar_latitude', defs.BODYX, 'centric'),
           ('', '', '')),
    minmax('PLANETOGRAPHIC_SUB_SOLAR_LATITUDE', ('sub_solar_latitude', defs.BODYX, 'graphic'),
           ('', '', '')),
    minmax('PLANETOCENTRIC_SUB_OBSERVER_LATITUDE', ('sub_observer_latitude', defs.BODYX, 'centric'),
           ('', '', '')),
    minmax('PLANETOGRAPHIC_SUB_OBSERVER_LATITUDE', ('sub_observer_latitude', defs.BODYX, 'graphic'),
           ('', '', '')),
    minmax('SUB_SOLAR_IAU_LONGITUDE', ('sub_solar_longitude', defs.BODYX, 'iau', 'west'),
           ('', '', '')),
    minmax('SUB_OBSERVER_IAU_LONGITUDE', ('sub_observer_longitude', defs.BODYX, 'iau', 'west'),
           ('', '', '')),
    minmax('CENTER_RESOLUTION', ('center_resolution', defs.BODYX, 'u'),
           ('', '', '')),
    minmax('CENTER_DISTANCE', ('center_distance', defs.BODYX, 'obs'),
           ('', '', '')),
    minmax('CENTER_PHASE_ANGLE', ('center_phase_angle', defs.BODYX),
           ('', '', '')),
    single('DIAMETER_IN_PIXELS', ('body_diameter_in_pixels', defs.BODYX),
           ('', '', '')),
    single('NORTH_POLE_CLOCK_ANGLE', ('pole_clock_angle', defs.BODYX),
           ('', '', '')),
    single('NORTH_POLE_POSITION_ANGLE', ('pole_position_angle', defs.BODYX),
           ('', '', '')),
    single('CENTER_X_COORDINATE', ('center_coordinate', defs.BODYX, 'u'),
           ('', '', '')),
    single('CENTER_Y_COORDINATE', ('center_coordinate', defs.BODYX, 'v'),
           ('', '', '')),
)
"""Every body column this package can compute, keyed by template NAME."""
