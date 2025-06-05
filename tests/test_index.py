################################################################################
# tests/test_index.py
################################################################################
import unittest
import pdstable
import numpy as np

import tests.unittester_support as unit


class Test_Index_Common(unittest.TestCase):

    #===========================================================================
    # test cumulative file
    def test_supplemental_index__cumulative(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*_0999_supplemental_index.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/')

        # Test labels
        for file in files:
            print()
            print('Reading', file)
            table = pdstable.PdsTable(file)

    #===========================================================================
    # test supplemental index common fields
    def test_supplemental_index_common(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*_supplemental_index.lbl')
        files = unit.exclude(files, 'templates/', 'old/', '__skip/')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # verify # rows, columns
            self.assertEqual(table.info.rows, len(table.column_values['VOLUME_ID']), file)
            self.assertEqual(table.info.columns, len(table.keys), file)

            # validate column values
            self.assertIsInstance(table.column_values['VOLUME_ID'][0], np.str_, file)
            self.assertIsInstance(table.column_values['FILE_SPECIFICATION_NAME'][0], np.str_, file)
            self.assertIsInstance(table.column_values['PRODUCT_CREATION_TIME'][0], np.str_, file)
            self.assertIsInstance(table.column_values['START_TIME'][0], np.str_, file)
            self.assertIsInstance(table.column_values['STOP_TIME'][0], np.str_, file)


#########################################
if __name__ == '__main__':
    unittest.main(verbosity=2)
################################################################################
