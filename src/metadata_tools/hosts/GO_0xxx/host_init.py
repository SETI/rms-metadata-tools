"""Initialize the Galileo SSI (GLL SSI) host module.

Importing this module for its side effects initializes the ``oops`` SSI host and
registers the geometry backplane columns. Host entry scripts import it before
generating any tables.
"""
import oops.hosts.galileo.ssi as ssi

ssi.initialize()

import metadata_tools.columns  # noqa: E402, F401  (side-effect import)
