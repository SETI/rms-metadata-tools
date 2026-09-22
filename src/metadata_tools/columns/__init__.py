"""The geometry column computation catalogs.

This package says how to *compute* each geometry column; the host's label
templates say which columns exist, in what order, and with what width, null
value, and valid range. :mod:`metadata_tools.geometry_support.label_schema`
joins the two on the column NAME.

Callers import it as ``import metadata_tools.columns as col`` and reach the
catalogs through :func:`~metadata_tools.columns.catalog.get_catalog` and
:func:`~metadata_tools.columns.catalog.name_map`.

Nothing in this package may import ``metadata_tools.geometry_support``:
``geometry_support.record`` imports this package, so the dependency has to run
one way only. ``tests/test_columns_import_lint.py`` enforces it.
"""
from metadata_tools.bodies import get_bodies_registry
from metadata_tools.columns.body import BODY_CATALOG
from metadata_tools.columns.catalog import (
    ColumnSpec,
    get_catalog,
    name_map,
)
from metadata_tools.columns.ring import RING_CATALOG
from metadata_tools.columns.sky import SKY_CATALOG
from metadata_tools.columns.sun import SUN_CATALOG

__all__ = [
    'BODY_CATALOG',
    'RING_CATALOG',
    'SKY_CATALOG',
    'SUN_CATALOG',
    'ColumnSpec',
    'get_bodies_registry',
    'get_catalog',
    'name_map',
]
