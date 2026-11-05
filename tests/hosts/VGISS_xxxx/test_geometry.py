################################################################################
# tests/hosts/VGISS_xxxx/test_geometry.py: Voyager ISS geometry tables
################################################################################
"""Voyager ISS geometry tables in the $RMS_METADATA holdings."""
import csv
import os

import numpy as np
import pdstable
import pytest

import tests.archive_support as support

# These tests read pre-generated tables from the $RMS_METADATA holdings tree;
# they are excluded from the default run (see the requires_archive marker in
# pyproject.toml and scripts/run-all-checks.sh --integration).
pytestmark = pytest.mark.requires_archive

COLLECTIONS = ('VGISS_5xxx', 'VGISS_6xxx', 'VGISS_7xxx', 'VGISS_8xxx')
EXCLUDE = ('templates/', 'old/', '__skip/',
           'VGISS_5999/', 'VGISS_6999/', 'VGISS_7999/', 'VGISS_8999/')

# Every body a Voyager ISS table may name: the primaries and selections of the
# mission table, and the Sun, which a target may name
BODIES = {'SUN', 'JUPITER', 'SATURN', 'URANUS', 'NEPTUNE',
          'IO', 'EUROPA', 'GANYMEDE', 'CALLISTO', 'METIS', 'ADRASTEA', 'AMALTHEA',
          'THEBE', 'HIMALIA',
          'MIMAS', 'ENCELADUS', 'TETHYS', 'DIONE', 'RHEA', 'TITAN', 'HYPERION',
          'IAPETUS', 'PHOEBE', 'JANUS', 'EPIMETHEUS', 'HELENE', 'TELESTO', 'CALYPSO',
          'ATLAS', 'PROMETHEUS', 'PANDORA', 'PAN',
          'MIRANDA', 'ARIEL', 'UMBRIEL', 'TITANIA', 'OBERON', 'CORDELIA', 'OPHELIA',
          'BIANCA', 'CRESSIDA', 'DESDEMONA', 'JULIET', 'PORTIA', 'ROSALIND', 'BELINDA',
          'PUCK',
          'TRITON', 'NEREID', 'NAIAD', 'THALASSA', 'DESPINA', 'GALATEA', 'LARISSA',
          'PROTEUS'}


def _files(pattern: str) -> list[str]:
    """Return the Voyager ISS files matching a pattern, skipping if there are none.

    Parameters:
        pattern: Glob pattern for the file names.

    Returns:
        The matching files under the Voyager ISS collections of $RMS_METADATA.
    """
    files: list[str] = []
    for collection in COLLECTIONS:
        files += support.match(os.path.join(support.metadata_tree(), collection), pattern)
    files = support.exclude(files, *EXCLUDE)
    if not files:
        pytest.skip(f'no Voyager ISS {pattern} files under $RMS_METADATA')
    return files


#===============================================================================
def test_geometry_common() -> None:
    """Every summary table's VOLUME_ID column matches the volume in the filename."""
    for file in _files('*_summary.lbl'):
        table = pdstable.PdsTable(file)
        volume = os.path.basename(file)[:10]
        assert np.all(table.column_values['VOLUME_ID'] == volume), file


def test_geometry_body() -> None:
    """Body rows name known bodies, and their angles lie within their ranges."""
    for file in _files('*_body_summary.lbl'):
        table = pdstable.PdsTable(file)
        names = {str(name).strip() for name in table.column_values['BODY_NAME']}
        assert names <= BODIES, (file, names - BODIES)
        for key in ('PLANETOCENTRIC_LATITUDE', 'PLANETOGRAPHIC_LATITUDE'):
            support.bounds(file, table, key, min_val=-90, max_val=90)
        for key in ('IAU_LONGITUDE', 'LOCAL_HOUR_ANGLE'):
            support.bounds(file, table, key, min_val=0, max_val=360)
        for key in ('PHASE_ANGLE', 'INCIDENCE_ANGLE', 'EMISSION_ANGLE'):
            support.bounds(file, table, key, min_val=0, max_val=180)


def test_geometry_ring() -> None:
    """Ring radii are positive and the ring angles lie within their ranges."""
    for file in _files('*_ring_summary.lbl'):
        table = pdstable.PdsTable(file)
        support.bounds(file, table, 'RING_RADIUS', min_val=0, max_val=1e9)
        support.bounds(file, table, 'RING_LONGITUDE', min_val=0, max_val=360)
        support.bounds(file, table, 'RING_PHASE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'SOLAR_RING_ELEVATION', min_val=-90, max_val=90)


def test_inventory_names_known_bodies() -> None:
    """Every inventory row belongs to its volume and names only known bodies."""
    for file in _files('*_inventory.csv'):
        volume = os.path.basename(file)[:10]
        with open(file, newline='', encoding='latin-1') as f:
            for row in csv.reader(f):
                assert row[0] == volume, file
                names = {name for name in row[2].split(',') if name}
                assert names <= BODIES, (file, row[1], names - BODIES)
