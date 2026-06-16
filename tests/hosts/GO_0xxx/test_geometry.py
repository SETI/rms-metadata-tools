################################################################################
# GOSSI-specific metadata geometry unit tests
################################################################################
import numpy as np
import pdstable
import pytest

#metadata_tools.util as util
#import metadata_tools.hosts.GO_0xxx.host_config as config
import tests.archive_support as support

#SYSTEMS_TABLE = util.convert_systems_table(config.SYSTEMS_TABLE, config.SCLK_BASES)

# These tests read pre-generated tables/labels from the $RMS_METADATA holdings
# tree; they are excluded from the default run (see the requires_archive marker
# in pyproject.toml and scripts/run-all-checks.sh --integration).
pytestmark = pytest.mark.requires_archive


#===============================================================================
# test geometry common fields
def test_geometry_common() -> None:

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

    # Get labels to test
    files = support.match(support.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
    files = support.exclude(files, 'templates/', 'old/', '__skip/', '_ring_', '_sky_', 'GO_0999/')

    # Test labels, 'GO_0999/
    print()
    for file in files:
        print('Reading', file)
        _ = pdstable.PdsTable(file)

#            system, secondaries = util.get_system(SYSTEMS_TABLE, sclk, config.SCLK_BASES)

#            body = table.column_values['BODY_NAME']

        # validate value bounds
# These bounds only apply to the Jupiter orbits, if any.
#            support.bounds(file, table, 'SUB_SOLAR_PLANETOCENTRIC_LATITUDE',
#                        min_val=-30, max_val=30)
#            support.bounds(file, table, 'SUB_SOLAR_PLANETOGRAPHIC_LATITUDE',
#                        min_val=-30, max_val=30)
#            support.bounds(file, table, 'SUB_OBSERVER_PLANETOCENTRIC_LATITUDE',
#                        min_val=-35, max_val=35)
#            support.bounds(file, table, 'SUB_OBSERVER_PLANETOGRAPHIC_LATITUDE',
#                        min_val=-35, max_val=35)


#===============================================================================
# test geometry ring fields
def test_geometry_ring() -> None:

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

        #################### Slightly exceeds 90 deg in GO_0022
#            support.bounds(file, table, 'RING_CENTER_EMISSION_ANGLE', min_val=-30, max_val=30)

        support.bounds(file, table, 'NORTH_BASED_CENTER_EMISSION_ANGLE',
                    min_val=35, max_val=145)
        support.bounds(file, table, 'SOLAR_RING_CENTER_OPENING_ANGLE',
                    min_val=-35, max_val=35)
        support.bounds(file, table, 'OBSERVER_RING_CENTER_OPENING_ANGLE',
                    min_val=-30, max_val=30)
################################################################################
