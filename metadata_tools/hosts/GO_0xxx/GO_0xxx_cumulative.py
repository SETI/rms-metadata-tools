#!/usr/bin/env python
################################################################################
# GO_0xxx_cumulative.py: Generate cumulative files and labels for Galileo SSI.
#
# Usage:
#    GO_0xxx_cumulative.py [-h] [--labels [labels ...]]
#                          [--exclude [exclude ...]]
#                          input_tree output_tree [volume]
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
#                            If given, labels are generated for existing files.
#
#    Cumulative Arguments:
#      --exclude [exclude ...], -e [exclude ...]
#                            List of volumes to exclude.
#
#   e.g., python3 GO_0xxx_cumulative.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA/GO_0xxx/GO_0999/
#         python3 GO_0xxx_cumulative.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA/GO_0xxx/GO_0999/ GO_0017
#
# Procedure:
#  1) Create the supplemental index files in the input tree using
#     GO_0xxx_index.py.
#  2) Create the geometry tables in the input tree using GO_0xxx_geometry.py.
#  3) Edit this script for your new host and run to generate the cumulative
#     tables in the output tree.
#
################################################################################
import host_init
import metadata_tools.cumulative_support as cml

cml.create_cumulative_indexes(host='GOISS',
                              exclude=['GO_0999'])
################################################################################
