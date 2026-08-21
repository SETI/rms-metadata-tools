################################################################################
# test_geometry_sun_label.py: Structural contract for the sun summary label.
#
# The full geometry pipeline (SPICE + the holdings tree) generates the sun
# summary .tab and validates the label against it. That path is archive-gated,
# so this hermetic test guards the label fragment against column-count / width
# drift directly from the column definitions and FORMAT_DICT: every data column
# emitted by SUN_SUMMARY_COLUMNS must have exactly one matching COLUMN object
# (of the right field width) in templates/sun_summary_columns.lbl.
################################################################################
"""Guard templates/sun_summary_columns.lbl against the sun column definitions."""

import pathlib
import re

from filecache import FCPath

from metadata_tools.columns import sun
from metadata_tools.geometry_support import formats

_FRAGMENT = (
    FCPath(pathlib.Path(__file__).resolve().parents[1])
    / 'src'
    / 'metadata_tools'
    / 'templates'
    / 'sun_summary_columns.lbl'
)


def _expected_widths() -> list[int]:
    """Field widths of the data columns emitted by SUN_SUMMARY_COLUMNS.

    Each column description emits ``number_of_values`` fields (1 or 2) of the
    ``column_width`` recorded in FORMAT_DICT/ALT_FORMAT_DICT.
    """
    widths: list[int] = []
    for column_desc in sun.SUN_SUMMARY_COLUMNS:
        key = str(column_desc[0][0])
        if len(column_desc) > 2:
            fmt = formats.ALT_FORMAT_DICT[(key, str(column_desc[2]))]
        else:
            fmt = formats.FORMAT_DICT[key]
        number_of_values, column_width = fmt[1], fmt[2]
        widths += [column_width] * number_of_values
    return widths


def _label_widths() -> list[int]:
    """Field widths of the COLUMN objects in sun_summary_columns.lbl, in order.

    The width comes from an ``F``/``A`` FORMAT; a ``DATA_TYPE = TIME`` column
    carries no FORMAT and uses the 25-character ISO width from FORMAT_DICT.
    """
    with _FRAGMENT.open('r') as f:
        text = f.read()
    # Split on column starts; the lookbehind avoids matching END_OBJECT = COLUMN.
    blocks = re.split(r'(?<!END_)OBJECT\s*=\s*COLUMN', text)[1:]
    widths: list[int] = []
    for block in blocks:
        body = block.split('END_OBJECT')[0]
        fmt = re.search(r'FORMAT\s*=\s*"?[FA](\d+)', body)
        if fmt:
            widths.append(int(fmt.group(1)))
        elif 'DATA_TYPE' in body and 'TIME' in body:
            widths.append(25)
        else:  # pragma: no cover - a column with neither is a template error
            raise AssertionError(f'COLUMN has no parseable width:\n{body}')
    return widths


def test_sun_label_matches_column_definitions() -> None:
    """Every SUN_SUMMARY_COLUMNS data field has a matching COLUMN of equal width."""
    assert _label_widths() == _expected_widths()
