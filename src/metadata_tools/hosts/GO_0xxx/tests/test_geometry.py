################################################################################
# GOSSI-specific metadata geometry unit tests
################################################################################
import unittest

import numpy as np
import pdstable

#metadata_tools.util as util
#import metadata_tools.hosts.GO_0xxx.host_config as config
import tests.unittester_support as unit

#SYSTEMS_TABLE = util.convert_systems_table(config.SYSTEMS_TABLE, config.SCLK_BASES)

class TestGeometryGOSSI(unittest.TestCase):

    #===========================================================================
    # test geometry common fields
    def test_geometry_common(self) -> None:

        # Get labels to test
        files = unit.match(unit.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
        files = unit.exclude(files, 'templates/', 'old/', '__skip/', 'GO_0999/')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # validate column values
            volume = file.split('/')[-1][0:7]
            assert np.any(np.where(table.column_values['VOLUME_ID'] != volume)) != np.True_, file

    #===========================================================================
    # test geometry body fields
    def test_geometry_body(self) -> None:

        # Get labels to test
        files = unit.match(unit.METADATA, '*_summary.lbl')  # type: ignore[arg-type]
        files = unit.exclude(files, 'templates/', 'old/', '__skip/', '_ring_', '_sky_', 'GO_0999/')

        # Test labels, 'GO_0999/
        print()
        for file in files:
            print('Reading', file)
            _ = pdstable.PdsTable(file)

#            system, secondaries = util.get_system(SYSTEMS_TABLE, sclk, config.SCLK_BASES)

#            body = table.column_values['BODY_NAME']

            # validate value bounds
# These bounds only apply to the Jupiter orbits, if any.
#            unit.bounds(self, file, table, 'SUB_SOLAR_PLANETOCENTRIC_LATITUDE',
#                        min_val=-30, max_val=30)
#            unit.bounds(self, file, table, 'SUB_SOLAR_PLANETOGRAPHIC_LATITUDE',
#                        min_val=-30, max_val=30)
#            unit.bounds(self, file, table, 'SUB_OBSERVER_PLANETOCENTRIC_LATITUDE',
#                        min_val=-35, max_val=35)
#            unit.bounds(self, file, table, 'SUB_OBSERVER_PLANETOGRAPHIC_LATITUDE',
#                        min_val=-35, max_val=35)

    #===========================================================================
    # test geometry ring fields
    def test_geometry_ring(self) -> None:

        # Get labels to test
        files = unit.match(unit.METADATA, '*ring_summary.lbl')  # type: ignore[arg-type]
        files = unit.exclude(files, 'templates/', 'old/', '__skip/', '_body_', '_sky_', 'GO_0999/')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # validate value bounds
            unit.bounds(self, file, table, 'NORTH_BASED_INCIDENCE_ANGLE',
                        min_val=35, max_val=145)
            unit.bounds(self, file, table, 'SOLAR_RING_ELEVATION', min_val=-35, max_val=35)
            unit.bounds(self, file, table, 'RING_CENTER_INCIDENCE_ANGLE', min_val=60, max_val=90)
            unit.bounds(self, file, table, 'NORTH_BASED_CENTER_INCIDENCE_ANGLE',
                        min_val=35, max_val=145)

            #################### Slightly exceeds 90 deg in GO_0022
#            unit.bounds(self, file, table, 'RING_CENTER_EMISSION_ANGLE', min_val=-30, max_val=30)

            unit.bounds(self, file, table, 'NORTH_BASED_CENTER_EMISSION_ANGLE',
                        min_val=35, max_val=145)
            unit.bounds(self, file, table, 'SOLAR_RING_CENTER_OPENING_ANGLE',
                        min_val=-35, max_val=35)
            unit.bounds(self, file, table, 'OBSERVER_RING_CENTER_OPENING_ANGLE',
                        min_val=-30, max_val=30)


#########################################
if __name__ == '__main__':
    unittest.main(verbosity=2)
################################################################################
