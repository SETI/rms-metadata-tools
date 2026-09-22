"""Column computation catalog for sky geometry tables.

This module names every sky geometry column this package knows how to compute
and says how: the backplane key describing the inertial pointing of each pixel
on the sky, and the unit conversion applied to the result.

Whether a column is actually produced -- and in what order, with what width,
null value, and valid range -- is decided by the host's label template, not
here. An entry no template names is simply unused. See
:mod:`metadata_tools.columns.catalog`.
"""
from metadata_tools.columns.catalog import ColumnSpec, minmax

SKY_CATALOG: tuple[ColumnSpec, ...] = (
    minmax('RIGHT_ASCENSION',
           ('right_ascension', ()),
           ('', '', ''), flag='360', overflow='%10.5f'),
    minmax('DECLINATION',
           ('declination', ()),
           ('', '', ''), flag='DEG', overflow='%10.5f'),
)
"""Every sky column this package can compute, keyed by template NAME."""
