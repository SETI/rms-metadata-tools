"""Initialize the Cassini ISS host module.

Importing this module for its side effects initializes the ``rms-host-cassini``
ISS host. It is imported by this host's ``geometry_config`` module, which the
config registry loads lazily on the first ``get_geometry_config()`` call. The body
registry (``metadata_tools.bodies``) is built lazily on its own first call and
needs no import here.
"""
from host_cassini.oops import CassiniISS

CassiniISS.initialize()
