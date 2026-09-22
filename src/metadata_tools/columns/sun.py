"""Column computation catalog for sun geometry tables.

This module names every sun geometry column this package knows how to compute
and says how: the backplane key describing the Sun as seen in each observation,
and the unit conversion applied to the result.

The sun table is not wired into the pipeline; see
:class:`metadata_tools.geometry_support.tables.SunTable` for the blocker. The
catalog and its template are kept in step so enabling it stays a small change.

Whether a column is actually produced -- and in what order, with what width,
null value, and valid range -- is decided by the host's label template, not
here. An entry no template names is simply unused. See
:mod:`metadata_tools.columns.catalog`.
"""
from metadata_tools.columns.catalog import ColumnSpec, minmax, single

SUN_CATALOG: tuple[ColumnSpec, ...] = (
    minmax('PLANETOCENTRIC_LATITUDE',
           ('latitude', 'SUN', 'centric'),
           ('', '', '')),
    minmax('PLANETOGRAPHIC_LATITUDE',
           ('latitude', 'SUN', 'graphic'),
           ('', '', '')),
    minmax('IAU_LONGITUDE',
           ('longitude', 'SUN', 'iau', 'west'),
           ('', '', '')),
    minmax('LONGITUDE_WRT_OBSERVER',
           ('longitude', 'SUN', 'obs', 'west', -180),
           ('', '', '')),
    minmax('FINEST_SURFACE_RESOLUTION',
           ('finest_resolution', 'SUN'),
           ('', '', ''), overflow='%10.4e'),
    minmax('COARSEST_SURFACE_RESOLUTION',
           ('coarsest_resolution', 'SUN'),
           ('', '', ''), overflow='%10.4e'),
    minmax('SURFACE_DISTANCE',
           ('distance', 'SUN'),
           ('', '', ''), overflow='%12.5e'),
    minmax('SURFACE_INTERCEPT_TIME',
           ('event_time', 'SUN'),
           ('', '', ''), overflow='%25s'),
    minmax('PLANETOCENTRIC_SUB_OBSERVER_LATITUDE',
           ('sub_observer_latitude', 'SUN', 'centric'),
           ('', '', '')),
    minmax('PLANETOGRAPHIC_SUB_OBSERVER_LATITUDE',
           ('sub_observer_latitude', 'SUN', 'graphic'),
           ('', '', '')),
    minmax('SUB_OBSERVER_IAU_LONGITUDE',
           ('sub_observer_longitude', 'SUN', 'iau', 'west'),
           ('', '', '')),
    minmax('CENTER_RESOLUTION',
           ('center_resolution', 'SUN', 'u'),
           ('', '', ''), overflow='%10.4e'),
    minmax('CENTER_DISTANCE',
           ('center_distance', 'SUN', 'obs'),
           ('', '', ''), overflow='%12.5e'),
    minmax('RADIUS_IN_PIXELS',
           ('radius_in_pixels', 'SUN'),
           ('', '', ''), overflow='%12.5e'),
    single('CENTER_X_COORDINATE',
           ('center_coordinate', 'SUN', 'x'),
           ('', '', ''), overflow='%12.5e', link_id=1, link='null'),
    single('CENTER_Y_COORDINATE',
           ('center_coordinate', 'SUN', 'y'),
           ('', '', ''), overflow='%12.5e', link_id=1, link='null'),
)
"""Every sun column this package can compute, keyed by template NAME."""
