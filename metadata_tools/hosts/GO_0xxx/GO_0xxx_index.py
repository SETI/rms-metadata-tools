#!/usr/bin/env python
##########################################################################################
# GO_0xxx_index.py: Generate supplemental index tables and labels for Galileo SSI.
#
# Usage:
#    python GO_0xxx_index.py [-h] [--labels [labels ...]] [--type type]
##                           volume_tree metadata_tree output_tree [volume]

#    options:
#      -h, --help            show this help message and exit
#
#    Common Arguments:
#      volume_tree           File path to the top to tree containing the volume
#                            files.
#      metadata_tree         File path to the top to tree containing the metadata
#                            files.
#      output_tree           File path to the top to tree in which to place the
#                            volume files.
#      volume                If given, only this volume is processed.
#      --labels [labels ...], -l [labels ...]
#                          If given, labels are generated for existing files.
#    Index Arguments:
#      --type type, -t type  Type of index file to create, e.g., "supplemental".
#
#   e.g., python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
#         python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ GO_0017
#
##########################################################################################
import host_init
import metadata_tools.index_support as idx
import index_config as config

idx.process_index('GO_0xxx_supplemental_index',
                  glob=config.glob)
##########################################################################################
