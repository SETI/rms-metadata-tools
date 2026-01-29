#!/usr/bin/env python
##########################################################################################
# GO_0xxx_cumulative.py: Generate cumulative files and labels for Galileo SSI.
#
# Usage:
#    GO_0xxx_cumulative.py [-h] [--labels [labels ...]] [--volumes [volumes ...]
#                          [--exclude [exclude ...]]
#                          output_dir
#
#    options:
#      -h, --help            show this help message and exit
#
#    Common Arguments:
#      output_dir            Directory in which to place the cumulative files.
#      --volumes [volumes, ...], -vv [volumes, ...]
#                            If given, only these volumes are processed.
#      --labels [labels ...], -l [labels ...]
#                            If given, labels are generated for existing files.
#
#    Cumulative Arguments:
#      --exclude [exclude ...], -e [exclude ...]
#                            List of volumes to exclude.
#
#   e.g., python3 GO_0xxx_cumulative.py $RMS_METADATA/GO_0xxx/GO_0999/
#         python3 GO_0xxx_cumulative.py $RMS_METADATA/GO_0xxx/GO_0999/ -vv GO_0017
#
##########################################################################################
import host_init
import metadata_tools.cumulative_support as cml

cml.create_cumulative_indexes('GO_0xxx_supplemental_index',
                              exclude=['GO_0999'])
##########################################################################################
