################################################################################
# host_init.py for GLL SSI
#
#  Initializes the host module.
#
################################################################################
import oops.hosts.galileo.ssi as ssi

ssi.initialize()

import sys  # noqa: E402  (must follow ssi.initialize())

sys.path.append('')             # needed so a GCP instance recognizes metadata_tools
import metadata_tools.columns  # noqa: E402, F401  (side-effect import)
