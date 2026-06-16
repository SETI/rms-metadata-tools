################################################################################
# tests/test_index.py
################################################################################
import numpy as np
import pdstable
import pytest

import tests.unittester_support as unit

# These tests read pre-generated tables/labels from the $RMS_METADATA holdings
# tree; they are excluded from the default run (see the requires_archive marker
# in pyproject.toml and scripts/run-all-checks.sh --integration).
pytestmark = pytest.mark.requires_archive


#===============================================================================
# test cumulative file
def test_supplemental_index__cumulative() -> None:

    # Get labels to test
    files = unit.match(unit.METADATA, '*_0999_supplemental_index.lbl')  # type: ignore[arg-type]
    files = unit.exclude(files, 'templates/', 'old/', '__skip/')

    # Test labels
    for file in files:
        print()
        print('Reading', file)
        _ = pdstable.PdsTable(file)


#===============================================================================
# test supplemental index common fields
def test_supplemental_index_common() -> None:

    # Get labels to test
    files = unit.match(unit.METADATA, '*_supplemental_index.lbl')  # type: ignore[arg-type]
    files = unit.exclude(files, 'templates/', 'old/', '__skip/')

    # Test labels
    print()
    for file in files:
        print('Reading', file)
        table = pdstable.PdsTable(file)

        # verify # rows, columns
        assert table.info.rows == len(table.column_values['VOLUME_ID']), file
        assert table.info.columns == len(table.keys), file

        # validate column values
        assert isinstance(table.column_values['VOLUME_ID'][0], np.str_), file
        assert isinstance(table.column_values['FILE_SPECIFICATION_NAME'][0], np.str_), file
        assert isinstance(table.column_values['PRODUCT_CREATION_TIME'][0], np.str_), file
        assert isinstance(table.column_values['START_TIME'][0], np.str_), file
        assert isinstance(table.column_values['STOP_TIME'][0], np.str_), file
################################################################################
