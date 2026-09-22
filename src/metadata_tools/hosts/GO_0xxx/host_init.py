"""Initialize the Galileo SSI (GLL SSI) host module.

Importing this module for its side effects initializes the ``oops`` SSI host.
It is imported by this host's ``geometry_config`` module, which the config
registry loads lazily on the first ``get_geometry_config()`` call. The body
registry (``metadata_tools.bodies``) is built lazily on its own first call and
needs no import here.
"""
import oops.hosts.galileo.ssi as ssi

ssi.initialize()
