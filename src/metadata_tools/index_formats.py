################################################################################
# index_formats.py - Column value/format helpers (split out of index_support.py).
#
# These were static methods on IndexTable. They are pure (no instance state), so
# they live here as module-level functions to keep index_support.py under 500
# lines and to make them directly unit-testable.
################################################################################
import ast

import fortranformat as ff

import metadata_tools.common as com


#===============================================================================
def _format_value(value, format):
    """Format a single value using a Fortran format code.

    Args:
        value (str): Value to format.
        format (str): FORTRAN-style format code.

    Returns:
        str: formatted value.
    """

    # format value
    line = ff.FortranRecordWriter('(' + format + ')')
    result = line.write([value])

    # add double quotes to string formats
    if format[0] == 'A':
        result = '"' + result.strip().ljust(len(result)) + '"'

    return result

#===============================================================================
def _format_parms(format):
    """Determine len and type corresopnding to a given FORTRAN format code..

    Args:
        format (str): FORTRAN_style format code.

    Returns:
        NamedTuple (width (int), data_type (str)):
            width     (int): Number of bytes required for a formatted value,
                      including any quotes.
            data_type (str): Data type corresponding to the format code.
    """

    data_types = {'A': 'CHARACTER',
                  'E': 'ASCII_REAL',
                  'F': 'ASCII_REAL',
                  'I': 'ASCII_INTEGER'}
    try:
        f = _format_value('0', format)
    except TypeError:
        f = _format_value(0, format)

    width = len(f)
    data_type = data_types[format[0]]

    return (width, data_type)

#==========================================================================
def _format_column(column_stub, value, count=None):
    """Format a column.

    Args:
        column_stub (list): Preprocessed column stub.
        value (str): Value to format.
        count (int): Number of items to process. If not given, the 'ITEMS' entry is
                     used.

    Returns:
        str: Formatted value.
    """
    logger = com.get_logger()

    # Get value parameters
    name = column_stub['NAME']
    format = column_stub['FORMAT'].strip('"')
    (width, data_type) = _format_parms(format)
    if not count:
        count = column_stub['ITEMS'] if column_stub['ITEMS'] else 1

    # Split multiple elements into individual columns and process recursively
    if count > 1:
        if not isinstance(value, (list, tuple)):
            value = count * [value]
        assert len(value) == count

        fmt_list = []
        for item in value:
            result = _format_column(column_stub, item, count=1)
            fmt_list.append(result)
        return ','.join(fmt_list)

    # Clean up strings
    if isinstance(value, str):
        value = value.strip()
        value = value.replace('\n', ' ')
        while ('  ' in value):
            value = value.replace('  ', ' ')
        value = value.replace('"', '')

    # Format the value
    try:
        result = _format_value(value, format)
    except TypeError:
        logger.warning("Invalid format: %s %s %s" % (name, value, format))
        result = width * "*"

    if len(result) > width:
        logger.warning("No second format: %s %s %s %s" % (name, value, format, result))

    # Validate the formatted value
    try:
        _ = ast.literal_eval(result)
    except (ValueError, SyntaxError):
        logger.warning('Format error for %s: %s' % (name, value))

    return result

#===============================================================================
def _get_column_values(pds3_table):
    """Build a list of column stubs.

    Args:
        pds3_table (Pds3Tabel): Object defining the table.

    Returns:
        list: Dictionaries containing relevant keyword values for each column.
    """
    column_stubs = []
    colnum = 1
    while True:
        try:
            name = pds3_table.old_lookup('NAME', colnum)
        except IndexError:
            break

        column_stubs += [
            {'NAME'          : name,
             'FORMAT'        : pds3_table.old_lookup('FORMAT', colnum),
             'ITEMS'         : pds3_table.old_lookup('ITEMS', colnum),
             'NULL_CONSTANT' : _get_null_value(pds3_table, colnum)}]

        colnum += 1

    return column_stubs

#===============================================================================
def _get_null_value(pds3_table, colnum):
    """Determine the null value for a column.

    Args:
        pds3_table (Pds3Tabel): Object defining the table.
        column (int): Column number.

    Returns:
        str|float: Null value.
    """

    # List of accepted Null keywords
    nullkeys = ['NULL_CONSTANT',
                'UNKNOWN_CONSTANT',
                'INVALID_CONSTANT',
                'MISSING_CONSTANT',
                'NOT_APPLICABLE_CONSTANT']

    # Check for a known null key in column stub
    nullval = None
    for key in nullkeys:
        if nullval := pds3_table.old_lookup(key, colnum):
            continue

    return nullval
