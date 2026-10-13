################################################################################
"""General host-specific definitions for Cassini ISS.

This module holds settings shared across the index, geometry, and
cumulative generators for the COISS_1xxx and COISS_2xxx collections.
"""
template_name = 'COISS_xxxx_supplemental_index'

################################################################################
# Data labels to include: narrow-angle (N) and wide-angle (W) images
################################################################################
glob: str = '[NW]*.LBL'

################################################################################
# Border allowed around every field of view for uncertainty in the spacecraft
# pointing, in radians. The engine expands each field of view by this angle,
# and the labels state it.
################################################################################
BORDER: float = 1.5e-4
