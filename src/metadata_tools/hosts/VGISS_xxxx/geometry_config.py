"""Host-specific definitions and utilities for Voyager ISS geometry generation.

This module defines the mission table and other settings used to compute geometry
tables for the VGISS_5xxx, VGISS_6xxx, VGISS_7xxx, and VGISS_8xxx collections.
"""
from typing import Any

from host_voyager.oops import VoyagerISS

import metadata_tools.hosts.VGISS_xxxx.host_init  # noqa: F401  (side-effect import)

##########################################################################################
# The geometry reads each volume's raw-image index, which has one row per image. The
# volume's full index has a row for every product of every image.
##########################################################################################
index_glob: str = 'VGISS_*_raw_image_index.lbl'


##########################################################################################
# Irregular moons to treat exactly as the regular children of their planets are. The
# engine considers only the regular children of a planet otherwise. Triton is regular
# in oops already.
##########################################################################################
EXTRA_CHILDREN: list[str] = ['HIMALIA', 'PHOEBE', 'NEREID']


##########################################################################################
# Calibration frames: the camera views the dark sky behind a closed shutter, its
# calibration lamps, or the calibration plaque, so the pointing says nothing about
# what the image holds. The index has no OBSERVATION_ID, so they are recognized by
# their TARGET_NAME.
##########################################################################################
CALIBRATION_TARGETS: frozenset[str] = frozenset({'DARK', 'CAL LAMPS', 'PLAQUE'})

#=========================================================================================
def is_calibration(observation: Any) -> bool:
    """Whether an observation is a calibration frame.

    Parameters:
        observation: The observation, whose ``dict`` holds its index row.

    Returns:
        True if the observation's TARGET_NAME is one of CALIBRATION_TARGETS.
    """
    return str(observation.dict['TARGET_NAME']).strip() in CALIBRATION_TARGETS


##########################################################################################
# MISSION TABLE:
#
#  Only time ranges for which arguments are required need to be included in the table.
#  Observations whose times are not in the mission table appear in the body table only
#  if they have a target, as per rules 4 and 5 below. Observations that match any
#  EXCEPTION are excluded from the time range, i.e., the time test is bypassed.
#
#  EXCEPTIONS may be either regular expressions to be matched against the OBSERVATION_ID
#  or functions declared above that take the OOPS observation as an argument and return
#  True or False. The Voyager index has no OBSERVATION_ID, so only functions are used.
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
#  The rows are keyed by time, not by spacecraft clock: one collection holds the images
#  of both spacecraft, whose clocks cannot be compared. One row covers both spacecraft
#  at a planet, since they select the same bodies there. Each row spans the images of
#  its encounter in the RMS Node's raw-image indexes, with a margin of days:
#
#   Jupiter  VG1 1978-12-11 to 1979-04-14   VG2 1979-04-15 to 1979-07-16
#   Saturn   VG1 1980-08-23 to 1980-12-15   VG2 1981-06-05 to 1981-09-05
#   Uranus                                  VG2 1985-11-06 to 1986-02-19
#   Neptune                                 VG2 1989-06-05 to 1989-09-29
#
#  Seventeen Saturn images have no time in the index (IMAGE_TIME "UNK"); they fall in
#  no row.
#
##########################################################################################
EXCEPTIONS: list[str] = ['is_calibration']
JUPITER_MOONS: list[str] = ['IO', 'EUROPA', 'GANYMEDE', 'CALLISTO',
                            'METIS', 'ADRASTEA', 'AMALTHEA', 'THEBE', 'HIMALIA']
SATURN_MOONS: list[str] = ['MIMAS', 'ENCELADUS', 'TETHYS', 'DIONE', 'RHEA', 'TITAN',
                           'HYPERION', 'IAPETUS', 'PHOEBE', 'JANUS', 'EPIMETHEUS',
                           'HELENE', 'TELESTO', 'CALYPSO', 'ATLAS', 'PROMETHEUS',
                           'PANDORA', 'PAN']
URANUS_MOONS: list[str] = ['MIRANDA', 'ARIEL', 'UMBRIEL', 'TITANIA', 'OBERON',
                           'CORDELIA', 'OPHELIA', 'BIANCA', 'CRESSIDA', 'DESDEMONA',
                           'JULIET', 'PORTIA', 'ROSALIND', 'BELINDA', 'PUCK']
NEPTUNE_MOONS: list[str] = ['TRITON', 'NEREID', 'NAIAD', 'THALASSA', 'DESPINA',
                            'GALATEA', 'LARISSA', 'PROTEUS']
MISSION_TABLE: list[Any] = [
#   PHASE   |   TIME RANGE       |  EXCEPTIONS | PRIMARY  | SECONDARIES | SELECTIONS | ADDITIONS
#--------------------------------------------------------------------------------------------------
  ('JUPITER ', ('1978-12-01',
                '1979-08-01'), EXCEPTIONS, 'JUPITER', [],  JUPITER_MOONS,     []),
  ('SATURN  ', ('1980-08-01',
                '1981-10-01'), EXCEPTIONS, 'SATURN',  [],  SATURN_MOONS,      []),
  ('URANUS  ', ('1985-10-01',
                '1986-03-01'), EXCEPTIONS, 'URANUS',  [],  URANUS_MOONS,      []),
  ('NEPTUNE ', ('1989-05-01',
                '1989-10-15'), EXCEPTIONS, 'NEPTUNE', [],  NEPTUNE_MOONS,     [])]

#=========================================================================================
def from_index(index_filename: Any, supplemental_index_filename: Any = None) -> list[Any]:
    """Return one observation per row of the raw-image index.

    Parameters:
        index_filename: Path to the label of the volume's raw-image index.
        supplemental_index_filename: Path to the label of the volume's supplemental
            index, which holds each image's start time and clock counts.

    Returns:
        The observations of the index, in row order.
    """
    observations: list[Any] = VoyagerISS.from_index(index_filename,
                                                    supplement=supplemental_index_filename)
    return observations
