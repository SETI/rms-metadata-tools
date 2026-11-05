"""General host-specific definitions for Voyager ISS.

This module holds settings shared across the index, geometry, and
cumulative generators for the VGISS_5xxx, VGISS_6xxx, VGISS_7xxx, and
VGISS_8xxx collections.
"""
template_name = 'VGISS_xxxx_supplemental_index'

################################################################################
# Data labels to include: one per image. Each image is archived as several
# products (RAW, CLEANED, CALIB, GEOMED, and the reseau and tiepoint tables);
# the geometry describes the raw image, whose field of view the cleaned and
# calibrated images share.
################################################################################
glob: str = 'C*_RAW.LBL'

################################################################################
# Border allowed around every field of view for uncertainty in the spacecraft
# pointing, in radians. The engine expands each field of view by this angle,
# and the labels state it.
#
# PROVISIONAL: the Voyager scan-platform C kernels are good to some tens of
# narrow-angle pixels (9.25 microradians each), far worse than Galileo's or
# Cassini's, so this is set to 1 milliradian, about 110 NAC pixels, pending a
# decision.
################################################################################
BORDER: float = 1.0e-3

################################################################################
# The rings that obscure and shadow the bodies of a system, by system name. The
# engine applies them in the masks of the geometry columns, and the body labels
# say so.
################################################################################
OPAQUE_RINGS: dict[str, str] = {'SATURN': 'SATURN_MAIN_RINGS'}
