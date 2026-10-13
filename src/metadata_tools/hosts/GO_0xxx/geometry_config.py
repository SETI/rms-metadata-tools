"""Host-specific definitions and utilities for Galileo SSI (GLL SSI) geometry generation.

This module defines the mission table and other settings used to compute geometry
tables for the GO_0xxx collection.
"""
from typing import Any

from hosts.galileo.ssi import SSI

import metadata_tools.hosts.GO_0xxx.host_init  # noqa: F401  (side-effect import)

##########################################################################################
# GO_0xxx arguments
##########################################################################################
SC: int = -77


##########################################################################################
# MISSION TABLE:
#
#  Only SCLK ranges for which arguments are required need to be included in the table.
#  Observations whose SCLK ranges are not in the mission table appear in the body table
#  only if they have a target, as per rules 4 and 5 below. Observations that match any
#  EXCEPTION are excluded from the SCLK range, i.e., the SCLK test is bypassed.
#
#  EXCEPTIONS may be either regular expressions to be matched against the OBSERVATION_ID
#  or functions declared below that take the OOPS observation as an argument and return
#  True or False.
#
#  RULES:
#   1. The primary and secondary bodies, if specified, are always included.
#   2. Children of the primary are included if they intersect the FOV. If
#      there are selections, then only the selected children are considered.
#   3. If there is no primary, all selections that intersect the FOV are included.
#   4. The target is always included.
#   5. If the target is a satellite, the parent is included.
#   6. Additions are included whenever they intersect the FOV, regardless of the primary.
#
##########################################################################################
EXCEPTIONS: list[str] = [r'.*XCAL',
              r'.*LCAL',
              r'.*GOPX',
              r'.*_CALIB',
              r'.*____HTMC',
              r'PHOCAL.*',
              r'STRCAL.*',
              r'.*CHECKOUT']
MISSION_TABLE: list[Any] = [
#   PHASE   |   SCLK_STARTs  |  EXCEPTIONS | PRIMARY | SECONDARIES | SELECTIONS | ADDITIONS
#--------------------------------------------------------------------------------------------------------------
  ('VENUS   ', ('00180626.00',
                '00190641.00'), EXCEPTIONS, 'VENUS',   [],           [],           []),
  ('EARTH I ', ('00609593.00',
                '00623035.00'), EXCEPTIONS, 'EARTH',   [],           ['EARTH',
                                                                      'MOON'],     []),
  ('EARTH II', ('01645330.00',
                '01654708.45'), EXCEPTIONS, 'EARTH',   [],           ['EARTH',
                                                                      'MOON'],     []),
  ('EMCONJ  ', ('01662361.00',
                '01663187.00'), EXCEPTIONS, '',        ['EARTH',
                                                        'MOON'],
                                                                     ['EARTH',
                                                                      'MOON'],     []),
  ('SL9     ', ('02488066.45',
                '02492218.00'), EXCEPTIONS, 'JUPITER', ['IO',
                                                        'EUROPA',
                                                        'GANYMEDE',
                                                        'CALLISTO'],
                                                                     ['IO',
                                                                      'EUROPA',
                                                                      'GANYMEDE',
                                                                      'CALLISTO'],
                                                                                   []),
  ('JUPITER ', ('03464059.00',
                '06475387.00'), EXCEPTIONS, 'JUPITER', [],           ['IO',
                                                                      'EUROPA',
                                                                      'GANYMEDE',
                                                                      'CALLISTO',
                                                                      'METIS',
                                                                      'ADRASTEA',
                                                                      'AMALTHEA',
                                                                      'THEBE'],
                                                                                   ['SATURN'])]

#=========================================================================================
def from_index(index_filename: Any, supplemental_index_filename: Any = None) -> list[Any]:
    """Return one observation per index row with a nonzero exposure.

    The host returns an observation for every row. Zero-exposure rows are dropped
    here, so the geometry tables hold the same rows as before.

    Parameters:
        index_filename: Path to the label of the index file.
        supplemental_index_filename: Path to the label of the supplemental index file,
            if any.

    Returns:
        The observations of the index, in row order, less those with zero exposure.
    """
    observations = SSI.from_index(index_filename, supplemental_index_filename)
    return [observation for observation in observations if observation.texp != 0]
