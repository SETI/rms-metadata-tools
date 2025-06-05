################################################################################
# tests/test_geometry.py
################################################################################
import unittest
import pdstable
import pdsparser
import numpy as np

import tests.unittester_support as unit


class Test_Geometry(unittest.TestCase):

    #===========================================================================
    # test inventory file
    def test_inventory(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*_inventory.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/')
#        from IPython import embed; print('+++++++++++++'); embed()

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            label = pdsparser.PdsLabel.from_file(file)

    #===========================================================================
    # test cumulative geometry file
    def test_geometry_cumulative(self):
        return
        # Get labels to test
##### this needs to be changed to match cumulative files
        files = unit.match(unit.METADATA, '*_summary.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/', '.ring_', '_sky_')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

    #===========================================================================
    # test geometry common fields
    def test_geometry_common(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*_summary.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # verify # rows, columns
            self.assertEqual(table.info.rows, len(table.column_values['VOLUME_ID']), file)
            self.assertEqual(table.info.columns, len(table.keys), file)

            # validate column types
            self.assertIsInstance(table.column_values['VOLUME_ID'][0], np.str_, file)
            self.assertIsInstance(table.column_values['FILE_SPECIFICATION_NAME'][0], np.str_, file)

    #===========================================================================
    # test geometry body fields
    def test_geometry_body(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*_summary.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/', '_ring_', '_sky_')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # validate column types
            self.assertIsInstance(table.column_values['BODY_NAME'][0], np.str_, file)

            # validate bounded values
            unit.bounds(self, file, table, 'PLANETOCENTRIC_LATITUDE', min=-90, max=90)
            unit.bounds(self, file, table, 'PLANETOGRAPHIC_LATITUDE', min=-90, max=90)
            unit.bounds(self, file, table, 'IAU_LONGITUDE')
            unit.bounds(self, file, table, 'LOCAL_HOUR_ANGLE')
            unit.bounds(self, file, table, 'LONGITUDE_WRT_OBSERVER', min=-180, max=180)
            unit.bounds(self, file, table, 'PHASE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'INCIDENCE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'EMISSION_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'PLANETOCENTRIC_SUB_SOLAR_LATITUDE', min=-90, max=90)
            unit.bounds(self, file, table, 'PLANETOGRAPHIC_SUB_SOLAR_LATITUDE', min=-90, max=90)
            unit.bounds(self, file, table, 'PLANETOCENTRIC_SUB_OBSERVER_LATITUDE', min=-90, max=90)
            unit.bounds(self, file, table, 'PLANETOGRAPHIC_SUB_OBSERVER_LATITUDE', min=-90, max=90)
            unit.bounds(self, file, table, 'SUB_SOLAR_IAU_LONGITUDE')
            unit.bounds(self, file, table, 'SUB_OBSERVER_IAU_LONGITUDE')
            unit.bounds(self, file, table, 'CENTER_PHASE_ANGLE', min=0, max=180)

    #===========================================================================
    # test geometry ring fields
    def test_geometry_ring(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*ring_summary.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # validate bounded values
            unit.bounds(self, file, table, 'RING_LONGITUDE')
            unit.bounds(self, file, table, 'SOLAR_HOUR_ANGLE')
            unit.bounds(self, file, table, 'RING_LONGITUDE_WRT_OBSERVER', min=-180, max=180)
            unit.bounds(self, file, table, 'RING_AZIMUTH')
            unit.bounds(self, file, table, 'RING_PHASE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'RING_INCIDENCE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'NORTH_BASED_INCIDENCE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'RING_EMISSION_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'NORTH_BASED_EMISSION_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'SOLAR_RING_ELEVATION', min=-90, max=90)
            unit.bounds(self, file, table, 'OBSERVER_RING_ELEVATION', min=-90, max=90)
            unit.bounds(self, file, table, 'EDGE_ON_RING_LONGITUDE')
            unit.bounds(self, file, table, 'EDGE_ON_SOLAR_HOUR_ANGLE')
            unit.bounds(self, file, table, 'SUB_SOLAR_RING_LONGITUDE')
            unit.bounds(self, file, table, 'SUB_OBSERVER_RING_LONGITUDE')
            unit.bounds(self, file, table, 'RING_CENTER_PHASE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'RING_CENTER_INCIDENCE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'RING_CENTER_NORTH_BASED_INCIDENCE_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'RING_CENTER_EMISSION_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'RING_CENTER_NORTH_BASED_EMISSION_ANGLE', min=0, max=180)
            unit.bounds(self, file, table, 'SOLAR_RING_OPENING_ANGLE', min=-90, max=90)
            unit.bounds(self, file, table, 'OBSERVER_RING_OPENING_ANGLE', min=-90, max=90)

    #===========================================================================
    # test geometry sky fields
    def test_geometry_sky(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*sky_summary.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # validate bounded values
            unit.bounds(self, file, table, 'RIGHT_ASCENSION')
            unit.bounds(self, file, table, 'DECLINATION', min=-90, max=90)


#########################################
if __name__ == '__main__':
    unittest.main(verbosity=2)
################################################################################
