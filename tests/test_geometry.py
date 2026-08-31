################################################################################
# tests/test_geometry.py
################################################################################
"""Geometry table and label tests against pre-generated $RMS_METADATA holdings."""
import numpy as np
import pdsparser
import pdstable
import pytest

import tests.archive_support as support

# These tests read pre-generated tables/labels from the $RMS_METADATA holdings
# tree; they are excluded from the default run (see the requires_archive marker
# in pyproject.toml and scripts/run-all-checks.sh --integration).
pytestmark = pytest.mark.requires_archive


#===============================================================================
# test inventory file
def test_inventory() -> None:
    """Every inventory label parses as a PDS label."""

    # Get labels to test
    files = support.match(support.METADATA, '*_inventory.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        _ = pdsparser.PdsLabel.from_file(file)


#===============================================================================
# test cumulative geometry file
def test_geometry_cumulative() -> None:
    """At least one cumulative summary label exists and parses as a PdsTable."""

    # Get labels to test
    files = support.match(support.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/')

    # Cumulative labels declare INDEX_TYPE == "CUMULATIVE" inside their single
    # nested TABLE object (BODY_SUMMARY_TABLE / RING_SUMMARY_TABLE /
    # SKY_SUMMARY_TABLE); per-volume labels use INDEX_TYPE == "SINGLE" and are
    # already exercised by test_geometry_common/_body/_ring/_sky.
    print()
    found_cumulative = False
    for file in files:
        label_dict = pdsparser.PdsLabel.from_file(file).as_dict()
        table_obj = next((v for v in label_dict.values()
                           if isinstance(v, dict) and 'INDEX_TYPE' in v), None)
        if table_obj is None or table_obj['INDEX_TYPE'] != 'CUMULATIVE':
            continue

        found_cumulative = True
        print('Reading', file)
        _ = pdstable.PdsTable(file)

    assert found_cumulative, 'No cumulative summary labels found under RMS_METADATA'


#===============================================================================
# test geometry common fields
def test_geometry_common() -> None:
    """Every summary table has consistent counts and string identifier columns."""

    # Get labels to test
    files = support.match(support.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # verify # rows, columns
        assert table.info.rows == len(table.column_values['VOLUME_ID']), file
        assert table.info.columns == len(table.keys), file

        # validate column types
        assert isinstance(table.column_values['VOLUME_ID'][0], np.str_), file
        assert isinstance(table.column_values['FILE_SPECIFICATION_NAME'][0], np.str_), file


#===============================================================================
# test geometry body fields
def test_geometry_body() -> None:
    """Body summary angle and latitude columns lie within their physical bounds."""

    # Get labels to test
    files = support.match(support.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/', '_ring_', '_sky_')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # validate column types
        assert isinstance(table.column_values['BODY_NAME'][0], np.str_), file

        # validate bounded values
        support.bounds(file, table, 'PLANETOCENTRIC_LATITUDE', min_val=-90, max_val=90)
        support.bounds(file, table, 'PLANETOGRAPHIC_LATITUDE', min_val=-90, max_val=90)
        support.bounds(file, table, 'IAU_LONGITUDE')
        support.bounds(file, table, 'LOCAL_HOUR_ANGLE')
        support.bounds(file, table, 'LONGITUDE_WRT_OBSERVER', min_val=-180, max_val=180)
        support.bounds(file, table, 'PHASE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'INCIDENCE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'EMISSION_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'PLANETOCENTRIC_SUB_SOLAR_LATITUDE',
                    min_val=-90, max_val=90)
        support.bounds(file, table, 'PLANETOGRAPHIC_SUB_SOLAR_LATITUDE',
                    min_val=-90, max_val=90)
        support.bounds(file, table, 'PLANETOCENTRIC_SUB_OBSERVER_LATITUDE',
                    min_val=-90, max_val=90)
        support.bounds(file, table, 'PLANETOGRAPHIC_SUB_OBSERVER_LATITUDE',
                    min_val=-90, max_val=90)
        support.bounds(file, table, 'SUB_SOLAR_IAU_LONGITUDE')
        support.bounds(file, table, 'SUB_OBSERVER_IAU_LONGITUDE')
        support.bounds(file, table, 'CENTER_PHASE_ANGLE', min_val=0, max_val=180)


#===============================================================================
# test geometry ring fields
def test_geometry_ring() -> None:
    """Ring summary angle and elevation columns lie within their physical bounds."""

    # Get labels to test
    files = support.match(support.METADATA, '*ring_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # validate bounded values
        support.bounds(file, table, 'RING_LONGITUDE')
        support.bounds(file, table, 'SOLAR_HOUR_ANGLE')
        support.bounds(file, table, 'RING_LONGITUDE_WRT_OBSERVER', min_val=-180, max_val=180)
        support.bounds(file, table, 'RING_AZIMUTH')
        support.bounds(file, table, 'RING_PHASE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'RING_INCIDENCE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'NORTH_BASED_INCIDENCE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'RING_EMISSION_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'NORTH_BASED_EMISSION_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'SOLAR_RING_ELEVATION', min_val=-90, max_val=90)
        support.bounds(file, table, 'OBSERVER_RING_ELEVATION', min_val=-90, max_val=90)
        support.bounds(file, table, 'EDGE_ON_RING_LONGITUDE')
        support.bounds(file, table, 'EDGE_ON_SOLAR_HOUR_ANGLE')
        support.bounds(file, table, 'SUB_SOLAR_RING_LONGITUDE')
        support.bounds(file, table, 'SUB_OBSERVER_RING_LONGITUDE')
        support.bounds(file, table, 'RING_CENTER_PHASE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'RING_CENTER_INCIDENCE_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'NORTH_BASED_CENTER_INCIDENCE_ANGLE',
                    min_val=0, max_val=180)
        support.bounds(file, table, 'RING_CENTER_EMISSION_ANGLE', min_val=0, max_val=180)
        support.bounds(file, table, 'NORTH_BASED_CENTER_EMISSION_ANGLE',
                    min_val=0, max_val=180)
        support.bounds(file, table, 'SOLAR_RING_CENTER_OPENING_ANGLE',
                    min_val=-90, max_val=90)
        support.bounds(file, table, 'OBSERVER_RING_CENTER_OPENING_ANGLE',
                    min_val=-90, max_val=90)


#===============================================================================
# test geometry sky fields
def test_geometry_sky() -> None:
    """Sky summary right ascension and declination lie within physical bounds."""

    # Get labels to test
    files = support.match(support.METADATA, '*sky_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # validate bounded values
        support.bounds(file, table, 'RIGHT_ASCENSION')
        support.bounds(file, table, 'DECLINATION', min_val=-90, max_val=90)
################################################################################
