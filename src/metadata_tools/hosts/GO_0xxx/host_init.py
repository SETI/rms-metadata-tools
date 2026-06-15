################################################################################
# host_init.py for GLL SSI
#
#  Initializes the host module.
#
################################################################################
import oops.hosts.galileo.ssi as ssi
ssi.initialize()

import sys                      ### This is needed to get a GCP instance to recognize
sys.path.append('')             ### the metadata_tools module
import metadata_tools.columns
