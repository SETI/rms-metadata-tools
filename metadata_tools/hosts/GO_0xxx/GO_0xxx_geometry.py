#!/usr/bin/env python
##########################################################################################
# GO_0xxx_geometry.py: Generates all geometry tables and labels for Galileo SSI.
#
# Usage:
#    python GO_0xxx_geometry.py [-h] [--labels [labels ...]]
#                               [--selection selection] [--exclude [exclude ...]]
#                               [--new_only [new_only ...]] [--first first]
#                               [--sampling sampling]
#                               metadata_tree output_tree
#
#    options:
#      -h, --help            show this help message and exit
#
#    Common Arguments:
#      metadata_tree         File path to the top to tree containing the metadata
#                            files, specifically the corrected index files.
#      output_tree           File path to the top to tree from which to read the
#                            supplemental index files, and in which to place the new
#                            geometry tables.
#      --volumes [volumes, ...], -v [volumes, ...]
#                            If given, only these volumes are processed.
#      --labels [labels ...], -l [labels ...]
#                            If given, labels are generated for existing files.
#
#    Geometry Arguments:
#      --selection selection
#                            A string containing:
#                               "S" to generate summary files;
#                               "D" to generate detailed files. (Not currently tested)
#      --exclude [exclude ...], -e [exclude ...]
#                            List of volumes to exclude.
#      --new_only [new_only ...], -n [new_only ...]
#                            Only metadata volumes that contain no output files are
#                            processed.
#      --first first, -f first
#                            If given, at most this many input files are processed
#                            in each volume.
#      --sampling sampling, -s sampling
#                            Pixel sampling density.
#
#   e.g., python3 GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/
#         python3 GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -v GO_0017
#         python3 GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA_TEST/GO_0xxx/ -p *C0349605600R*
#
##########################################################################################
import host_init
import metadata_tools.geometry_support as geom
import geometry_config as config

geom.process_tables('GO_0xxx_supplemental_index',
                    glob=config.glob,
                    index_glob=config.index_glob,
                    selection="S",
                    exclude=['GO_0999'])
##########################################################################################
