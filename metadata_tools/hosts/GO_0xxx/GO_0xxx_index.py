#!/usr/bin/env python
##########################################################################################
# GO_0xxx_index.py: Generate supplemental index tables and labels for Galileo SSI.
#
# Usage:
#    python GO_0xxx_index.py [-h] [--labels [labels ...]] [--type type]
#                            [--volumes [volumes ...]
#                            volume_tree metadata_tree output_tree
#
#    options:
#      -h, --help            show this help message and exit
#
#    Common Arguments:
#      volume_tree           Path to the top to tree containing the volume files,
#                            specifically the labels.
#      metadata_tree         Path to the top to tree containing the metadata files,
#                            specifically the corrected index files.
#      output_tree           Path to the top to tree in which to place the new
#                            supplemental files.
#      --volumes [volumes, ...], -vv [volumes, ...]
#                            If given, only these volumes are processed.
#      --labels [labels ...], -l [labels ...]
#                          If given, labels are generated for existing files.
#    Index Arguments:
#      --type type, -t type  Type of index file to create, e.g., "supplemental".
#
#   e.g., python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
#         python3 GO_0xxx_index.py $RMS_VOLUMES/GO_0xxx/ $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -vv GO_0017
#
##########################################################################################
import host_init    # imported for side effects
import metadata_tools.geometry_support as geom
import index_config as config

idx.process_index('GO_0xxx_supplemental_index',
                  glob=config.glob)
##########################################################################################
