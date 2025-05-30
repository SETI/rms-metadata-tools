#!/usr/bin/env python
################################################################################
# GO_0xxx_index.py: Generate supplemental index tables and labels for Galileo
# SSI.
#
# Usage:
#    GO_0xxx_index.py [-h] [--labels [labels ...]] [--type type]
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
# Procedure:
#  1) Point $RMS_METADATA and $RMS_VOLUMES to the top of the local metadata and
#     volume trees respectively., e.g.,
#
#         RMS_METADATA = ~/SETI/RMS/metadata_test
#         RMS_VOLUMES = ~/SETI/RMS/holdings/volumes
#
#  2) Copy and rename the supplemental label template from an existing host,
#     e.g.:
#
#         hosts/GO_0xxx/templates/GO_0xxx_index_supplemental.lbl
#
#  3) Follow the instructions in the supplemental label template file.
#
################################################################################
import host_init
import metadata_tools.index_support as idx

idx.process_index('GO_0xxx_supplemental_index',
                  glob='C0*')
################################################################################
