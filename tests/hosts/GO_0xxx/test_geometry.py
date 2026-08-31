################################################################################
# GOSSI-specific metadata geometry unit tests
################################################################################
"""GOSSI geometry table tests against pre-generated $RMS_METADATA holdings."""
import numpy as np
import pdstable
import pytest

import tests.archive_support as support

# These tests read pre-generated tables/labels from the $RMS_METADATA holdings
# tree; they are excluded from the default run (see the requires_archive marker
# in pyproject.toml and scripts/run-all-checks.sh --integration).
pytestmark = pytest.mark.requires_archive


#===============================================================================
# test geometry common fields
def test_geometry_common() -> None:
    """Every summary table's VOLUME_ID column matches the volume in the filename."""

    # Get labels to test
    files = support.match(support.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/', 'GO_0999/')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # validate column values
        volume = file.split('/')[-1][0:7]
        assert np.any(np.where(table.column_values['VOLUME_ID'] != volume)) != np.True_, file


#===============================================================================
# test geometry body fields
def test_geometry_body() -> None:
    """Body summary tables exist and their BODY_NAME column holds string values."""

    # Get labels to test
    files = support.match(support.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/', '_ring_', '_sky_', 'GO_0999/')
    assert files, 'no body summary labels found under $RMS_METADATA'

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # validate column values
        assert isinstance(table.column_values['BODY_NAME'][0], np.str_), file


#===============================================================================
# test geometry ring fields
def test_geometry_ring() -> None:
    """Ring summary values honor the GOSSI-specific angle bounds."""

    # Get labels to test
    files = support.match(support.METADATA, '*ring_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/', '_body_', '_sky_', 'GO_0999/')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # validate value bounds
        support.bounds(file, table, 'NORTH_BASED_INCIDENCE_ANGLE',
                    min_val=35, max_val=145)
        support.bounds(file, table, 'SOLAR_RING_ELEVATION', min_val=-35, max_val=35)
        support.bounds(file, table, 'RING_CENTER_INCIDENCE_ANGLE', min_val=60, max_val=90)
        support.bounds(file, table, 'NORTH_BASED_CENTER_INCIDENCE_ANGLE',
                    min_val=35, max_val=145)
        support.bounds(file, table, 'NORTH_BASED_CENTER_EMISSION_ANGLE',
                    min_val=35, max_val=145)
        support.bounds(file, table, 'SOLAR_RING_CENTER_OPENING_ANGLE',
                    min_val=-35, max_val=35)
        support.bounds(file, table, 'OBSERVER_RING_CENTER_OPENING_ANGLE',
                    min_val=-30, max_val=30)
################################################################################
