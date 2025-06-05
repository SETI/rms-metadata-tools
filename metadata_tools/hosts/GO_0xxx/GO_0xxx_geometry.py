#!/usr/bin/env python
################################################################################
# GO_0xxx_geometry.py: Generates all geometry tables and labels for Galileo SSI.
#
# Usage:
#    GO_0xxx_geometry.py [-h] [--labels [labels ...]]
#                             [--selection selection] [--exclude [exclude ...]]
#                             [--new_only [new_only ...]] [--first first]
#                             [--sampling sampling]
#                             input_tree output_tree [volume]
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
#    Geometry Arguments:
#      --selection selection
#                            A string containing: "S" to generate summary files;
#                            "D" to generate detailed files.
#      --exclude [exclude ...], -e [exclude ...]
#                            List of volumes to exclude.
#      --new_only [new_only ...], -n [new_only ...]
#                            Only volumes that contain no output files are
#                            processed.
#      --first first, -f first
#                            If given, at most this many input files are processed
#                            in each volume.
#      --sampling sampling, -s sampling
#                            Pixel sampling density.
#
#   e.g., python3 GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA/GO_0xxx/
#         python3 GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA/GO_0xxx/ GO_0017
#
# Procedure:
#  1) Create the supplemental index files in the input tree using
#     GO_0xxx_index.py.
#
#  2) Copy and rename the summary label templates from an existing host, e.g.:
#
#         hosts/GO_0xxx/templates/GO_0xxx_body_summary.lbl
#         hosts/GO_0xxx/templates/GO_0xxx_ring_summary.lbl
#
#  3) Follow the instructions in either summary label template file.
#
################################################################################
import host_init
import metadata_tools.geometry_support as geom

geom.process_tables('GO_0xxx_supplemental_index',
                    glob='GO_????_index.lbl',
                    selection="S",
                    exclude=['GO_0999'])
################################################################################
