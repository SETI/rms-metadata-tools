"""Host-specific definitions and utilities for Cassini ISS geometry generation.

This module defines the mission table and other settings used to compute geometry
tables for the COISS_1xxx and COISS_2xxx collections.
"""
from typing import Any

from host_cassini.oops import CassiniISS

import metadata_tools.hosts.COISS_xxxx.host_init  # noqa: F401  (side-effect import)

##########################################################################################
# COISS_xxxx arguments
##########################################################################################
SC: int = -82


##########################################################################################
# Irregular moons to treat exactly as the regular children of their planets are. The
# engine considers only the regular children of a planet otherwise.
##########################################################################################
EXTRA_CHILDREN: list[str] = ['HIMALIA', 'PHOEBE']


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
#   2. Children of the primary (its regular children and any EXTRA_CHILDREN)
#      are included if they intersect the FOV. If there are selections, then
#      only the selected children are considered.
#   3. If there is no primary, all selections that intersect the FOV are included.
#   4. The target is always included.
#   5. If the target is a satellite, the parent is included.
#   6. Additions are included whenever they intersect the FOV, regardless of the primary.
#
#  The SCLK ranges are 1999-08-01 to 1999-09-15 (Earth flyby), 1999-09-16 to 2002-07-11
#  (Jupiter, from the Earth flyby until the end of COISS_1007), and 2002-07-12 to
#  2017-09-16 (Saturn, from the start of COISS_1008 through the approach and tour). Jupiter
#  and Saturn span the cruise images between their encounters, as in the earlier
#  release of these tables; only the images before the Earth flyby (Venus, Spica and
#  the sky) have no primary.
#
##########################################################################################
EXCEPTIONS: list[str] = []
JUPITER_MOONS: list[str] = ['IO', 'EUROPA', 'GANYMEDE', 'CALLISTO',
                            'METIS', 'ADRASTEA', 'AMALTHEA', 'THEBE', 'HIMALIA']
SATURN_MOONS: list[str] = ['MIMAS', 'ENCELADUS', 'TETHYS', 'DIONE', 'RHEA', 'TITAN',
                           'HYPERION', 'IAPETUS', 'PHOEBE', 'JANUS', 'EPIMETHEUS',
                           'HELENE', 'TELESTO', 'CALYPSO', 'ATLAS', 'PROMETHEUS',
                           'PANDORA', 'PAN', 'METHONE', 'PALLENE', 'POLYDEUCES',
                           'DAPHNIS', 'ANTHE', 'AEGAEON']
MISSION_TABLE: list[Any] = [
#   PHASE   |   SCLK_STARTs       |  EXCEPTIONS | PRIMARY | SECONDARIES | SELECTIONS | ADDITIONS
#--------------------------------------------------------------------------------------------------
  ('EARTH   ', ('1312157197.240',
                '1316045223.124'), EXCEPTIONS, 'EARTH',   [],  ['EARTH', 'MOON'], []),
  ('JUPITER ', ('1316131624.014',
                '1405037836.010'), EXCEPTIONS, 'JUPITER', [],  JUPITER_MOONS,     []),
  ('SATURN  ', ('1405124236.165',
                '1884215387.221'), EXCEPTIONS, 'SATURN',  [],  SATURN_MOONS,      [])]

#=========================================================================================
def from_index(index_filename: Any, supplemental_index_filename: Any = None) -> list[Any]:
    """Return one observation per index row.

    Parameters:
        index_filename: Path to the label of the index file.
        supplemental_index_filename: Path to the label of the supplemental index file;
            unused, since the Cassini ISS index holds everything the host needs.

    Returns:
        The observations of the index, in row order.
    """
    observations: list[Any] = CassiniISS.from_index(index_filename)
    return observations
