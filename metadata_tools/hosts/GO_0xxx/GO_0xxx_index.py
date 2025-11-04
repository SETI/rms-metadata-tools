#!/usr/bin/env python
##########################################################################################
# GO_0xxx_index.py: Generate supplemental index tables and labels for Galileo SSI. Run
# this script from the host subdirectory.
#
# Usage:
#    python GO_0xxx_index.py [-h] [--labels [labels ...]] [--type type]
#
#    options:
#      -h, --help            show this help message and exit
#
#    Common Arguments:
#      input_tree            File path to the top to tree containing the volume
#                            files.
#      output_tree           File path to the top to tree in which to place the
#                            volume files.
#      volume                If given, only this volume is processed.
#      --labels [labels ...], -l [labels ...]
#                          If given, labels are generated for existing files.
#    Index Arguments:
#      --type type, -t type  Type of index file to create, e.g., "supplemental".
#
#   e.g., python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/
#         python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ GO_0017
#
##########################################################################################
import host_init
import metadata_tools.index_support as idx
import host_config as hconf

idx.process_index('GO_0xxx_supplemental_index',
                  glob=hconf.glob)
##########################################################################################
