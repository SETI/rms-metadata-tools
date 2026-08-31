"""Initialize the Galileo SSI (GLL SSI) host module.

Importing this module for its side effects initializes the ``oops`` SSI host and
registers the geometry backplane columns. It is imported by this host's
``geometry_config`` module, which the config registry loads lazily on the first
``get_geometry_config()`` call.
"""
import oops.hosts.galileo.ssi as ssi

ssi.initialize()

import metadata_tools.columns  # noqa: E402, F401  (side-effect import)
