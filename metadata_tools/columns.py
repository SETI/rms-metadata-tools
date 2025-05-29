################################################################################
# columns.py: Define geometry columns
################################################################################
import oops

import numpy as np
import metadata_tools.util as util
import metadata_tools.defs as defs

################################################################################
# Create a list of body IDs
################################################################################
def define_bodies(body_names):
    bodies = []
    for name in body_names:
        bod = oops.Body.lookup(name)
        bodies += [bod]
        bodies += bod.select_children("REGULAR")
    return {body.name: body for body in bodies}


BODIES = define_bodies(defs.BODY_NAMES)

#############################################
# Define geometry columns
#############################################
column_files = list(defs.COLUMN_DIR.glob('COLUMNS_*.py'))
for file in column_files:
    exec(open(file).read())
