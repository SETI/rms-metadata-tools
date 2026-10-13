"""General host-specific definitions and utilities for Galileo SSI (GLL SSI).

This module holds settings shared across the index, geometry, and
cumulative generators for the GO_0xxx collection.
"""
template_name = 'GO_0xxx_supplemental_index'

################################################################################
# Data labels to include
################################################################################
glob: str = 'C0*.LBL'

################################################################################
# Spacecraft clock modulo
################################################################################
SCLK_BASES: list[int] = [16777215, 91, 10, 8]
