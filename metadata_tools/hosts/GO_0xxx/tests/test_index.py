################################################################################
# GOSSI-specific metadata index unit tests
################################################################################
import unittest

import pdstable
#import pdsparser
import numpy as np

import tests.unittester_support as unit


class Test_Index_GOSSI(unittest.TestCase):

    #===========================================================================
    # test supplemental index fields
    def test_supplemental_index_GOSSI(self):

        # Get labels to test
        files = unit.match(unit.METADATA, '*_supplemental_index.lbl')
        files = unit.exclude(files, 'templates/', 'old/')

        # Test labels
        print()
        for file in files:
            print('Reading', file)
            table = pdstable.PdsTable(file)

            # validate column values
            self.assertIsInstance(table.column_values['TELEMETRY_FORMAT_ID'][0], np.str_, file)
            self.assertIsInstance(table.column_values['CUT_OUT_WINDOW'][0][0], np.int_, file)
            self.assertEqual(len(table.column_values['CUT_OUT_WINDOW'][0]), 4, file)
            self.assertIsInstance(table.column_values['TRUTH_WINDOW'][0][0], np.int_, file)
            self.assertEqual(len(table.column_values['TRUTH_WINDOW'][0]), 4, file)
            self.assertIsInstance(table.column_values['LIGHT_FLOOD_STATE_FLAG'][0], np.str_, file)
            self.assertIsInstance(table.column_values['EXPOSURE_TYPE'][0], np.str_, file)
            self.assertIsInstance(table.column_values['INVERTED_CLOCK_STATE_FLAG'][0], np.str_, file)
            self.assertIsInstance(table.column_values['ON_CHIP_MOSAIC_FLAG'][0], np.str_, file)
            self.assertIsInstance(table.column_values['INSTRUMENT_MODE_ID'][0], np.str_, file)
            self.assertIsInstance(table.column_values['HUFFMAN_TABLE_TYPE'][0], np.str_, file)
            self.assertIsInstance(table.column_values['ICT_DESPIKE_THRESHOLD'][0], np.int_, file)
            self.assertIsInstance(table.column_values['PRODUCT_VERSION_ID'][0], np.int_, file)
            self.assertIsInstance(table.column_values['ICT_QUANTIZATION_STEP_SIZE'][0], np.int_, file)
            self.assertIsInstance(table.column_values['ICT_ZIGZAG_PATTERN'][0], np.str_, file)
            self.assertIsInstance(table.column_values['COMPRESSION_QUANTIZATION_TABLE_ID'][0], np.str_, file)
            self.assertIsInstance(table.column_values['ENTROPY'][0], np.float64, file)
            self.assertIsInstance(table.column_values['START_TIME'][0], np.str_, file)
            self.assertIsInstance(table.column_values['STOP_TIME'][0], np.str_, file)
            self.assertIsInstance(table.column_values['SPACECRAFT_CLOCK_START_COUNT'][0], np.str_, file)
            self.assertIsInstance(table.column_values['SPACECRAFT_CLOCK_STOP_COUNT'][0], np.str_, file)


#########################################
if __name__ == '__main__':
    unittest.main(verbosity=2)
################################################################################
