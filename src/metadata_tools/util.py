################################################################################
# util.py: Utility functions
################################################################################
import datetime as dt
import sys
from typing import Any

import cspyce
import pdstable
from filecache import FCPath

import metadata_tools.defs as defs

# These helpers were split out of this module to keep every file under 500 lines
# (see plans/plan1_split_geometry_support.md for the analogous geometry split).
# They are re-exported here so callers keep using `util.<name>` unchanged.
from metadata_tools.util_ranges import (  # noqa: F401  (re-exported public API)
    NINETY_PERCENT_RANGE_DEGREES,
    _get_range_mod360,
    _ninety_percent_gap_degrees,
    pm,
    range_of_n_angles,
    smooth,
)
from metadata_tools.util_textfiles import (  # noqa: F401  (re-exported public API)
    append_txt_file,
    expandvars,
    read_txt_file,
    write_txt_file,
)


#===============================================================================
def dbprint(message):
    """Print a messaage to stderr with time stamp for degugging.

    Args:
        message (str): Mesaage to write.

    Returns: None
    """
#    return
    time = dt.datetime.now()#.strftime('%Y-%m-%d %H:%M:%S')
    print(f'{time} - {message}', file=sys.stderr, flush=True)

#===============================================================================
def PdsTable(label_path):
    """read a pds3table from an FCPath object.  To be replaced whenever pdstable is
       upgraded to use filecache.

    Args:
        label_path (str, Path, or FCPath): Path to the label file.

    Returns:
        pdstable.PdsTable: Table associated with the given label.
    """
    local_label_path = label_path.retrieve()
    _local_table_path = label_path.with_suffix('.tab').retrieve() # Retrieve table as well
    return pdstable.PdsTable(local_label_path)

#===============================================================================
def select_dir(tree, col, vol):
    """Determine the template directory for a given collection and volume.

    Args:
        tree (FCPath): Base tree path.
        col (str): Collection name.
        vol (str): Volume name.

    Returns:
        FCPath: Directory path.
    """
    if tree.parts[-1] != col:
        return tree / col / vol
    return tree / vol

#===============================================================================
def get_index_name(dir, vol_id, type):
    """Determine the name of the index file.

    Args:
        dir (str): Top dir for volume.
        vol_id (str): Volume ID.
        type (tstr): Index type.

    Returns:
        str: Index name.
    """

    # Name starts with volume id
    dir = dir.absolute()
    name = vol_id

    # Add type if given
    if type:
        name += '_' + type

    name += '_index'

    return name

#===============================================================================
def get_template_name(filename, volume_id, code_dir):
    """Determine the name of the label template.

    Args:
        filename (str): Name of table or label file.

    Returns:
        str: Index name.
    """
    collection = code_dir.name
    return filename.replace(volume_id, collection).split('.')[0]

#===============================================================================
def parse_template_name(template_name):
    """Determine host and index type from template name of the form:

        <host>_<index type>_index

    index_type cannot contain undescores.

    Args:
        template_name (str): Name of template file.

    Returns:
        str: Host name.
        str: index type.
    """
    base = template_name.split('_index')[0]
    parts = base.split('_')
    index_type = parts[-1]
    host = '_'.join(parts[0:-1])
    template_dir = defs.PARENT_DIR / FCPath('hosts') / FCPath(host) / FCPath('templates')

    return (host, index_type, template_dir)

#===============================================================================
def splitpath(path: str, string: str):               ### move to utilities
    """Split a path at a given string.

    Args:
        path (str, Path, or FCPath): Path to split.
        string (str):
            Search string. The path is split at the first occurrence and the search
            string is omitted.

    Returns:
        NamedTuple (lines (list), lnum (int)):
            lines: Lines comprising the output label.
            lnum: Line number in output label at which processing
                        is to continue.
    """
    parts = path.parts
    i = parts.index(string)
    return (FCPath('').joinpath(*parts[0:i]), FCPath('').joinpath(*parts[i+1:]))

#===============================================================================
def get_volume_subdir(path, volume_id):
    """Determine the Subdirectory of an input file relative to the volume dir.

    Args:
        path (str, Path, or FCPath): Input path or directory.

    Returns:
        str: Final directory in tree.
    """
    return splitpath(path, volume_id)[-1]
#    return path.split(volume_id)[-1]  ## not currently supprted by filecache

#===============================================================================
def replace(tree: list[Any], placeholder: str, name: str) -> Any:
    """Return a copy of the tree of objects, with each occurrence of the
    placeholder string replaced by the given name.  If a dictionary reference is
    detected, then it is evaluated.

    Args:
        tree (list): List containing the tree.
        placeholder (str): Placeholder to replace
        name (str): Replacement string.

    Returns:
        list: New tree with placeholder replaced by name.

    """

    new_tree: list[Any] = []
    for leaf in tree:
        # Main entries: replace placeholder and evaulate dict references
        if type(leaf) in (tuple, list):
            # replace placeholder
            replacement = replace(leaf, placeholder, name)

            # evaluate any dictionary references now that placeholders are resolved
            lrep = list(replacement)
            for i in range(len(lrep)):
                if isinstance(lrep[i], str) and '[' in lrep[i]:
                    lrep[i] = eval(lrep[i])
            replacement = tuple(lrep)

            new_tree.append(replacement)

        # Simple str with placeholders: replace placeholder and add to tree
        elif isinstance(leaf, str) and leaf.find(placeholder) != -1:
            new_tree.append(leaf.replace(placeholder, name))

        # Everything else: add to tree unchanged
        else:
            new_tree.append(leaf)

    if isinstance(tree, tuple):
        return tuple(new_tree)
    else:
        return new_tree

#===============================================================================
def replacement_dict(tree: list[Any], placeholder: str, names: list[str]) -> dict[str, Any]:
    """Create a dictionary of copies of the tree of objects, where each
    dictionary entry is keyed by a name in the list and returns a copy of the
    tree using that name as the replacement.

    Args:
        tree (list): List containing the tree.
        placeholder (str): Placeholder to replace
        name (list): List of replacement strings.

    Returns:
        dict: New dictionary.

    """

    result: dict[str, Any] = {}
    for name in names:
        result[name] = replace(tree, placeholder, name)

    return result

#===============================================================================
def replacement_fn(dict_name: str, name: str) -> str:
    """Create a replacement-able dictionary reference.

    Args:
        dict_name (str): Name of dictionary.
        name (str): Dictionary key, which could be a placeholder string.

    Returns:
        str: Dictionary reference keyed by possible placeholder name.

    """
    return dict_name + '["' + name + '"]'

#===============================================================================
def get_volume_glob(col):
    """Build a glob string to match all volumes in a collection.

    Args:
        col (str): Collection name, e.g., GO_xxxx.

    Returns:
        str: Glob string.

    """
    parts = col.rsplit('_', 1)
    id = parts[1]
    id_glob = id.replace('x', '[0-9]')
    volume_glob = parts[0] + '_' + id_glob

    return volume_glob

#===============================================================================
def add_by_base(x_digits, y_digits, bases):           ### move to utilities
    """Add numbers represented using the specified bases.

    Args:
        x_digits (list): Digits (int) representing the first operand.
        y_digits (list): Digits (int) representing the second operand.
        bases (list): Bases (int) for each position.

    Returns:
        list: Digits (int) representing the result.

    """
    result = [0]*(len(bases)+1)
    for i, (x_digit, y_digit, base) in \
      enumerate(zip(reversed(x_digits), reversed(y_digits), reversed(bases))):
        result[i] += (x_digit + y_digit) % base
        result[i+1] += (x_digit + y_digit) // base
    return list(reversed(result))

#===============================================================================
def rebase(x, bases, ceil=False):    ### move to utilities
    """Convert a decimal number to a different base.

    Args:
        x (int): Number to convert.
        bases (list): Base (int) to use for each decimal place.

    Returns:
        NamedTuple (digits (list), over (int)):
            digits: Digits (int) in the new base.
            overflow:
                Remaining quantity, if any, exceeding the maximum value that can be
                represented by the given bases.
    """
    import math

    digits = []
    for base in reversed(bases):
        digit = x % base
        if not ceil:
            digit = int(digit)
        else:
            digit = math.ceil(digit)
        digits.append(digit)

        x //= base
    return (list(reversed(digits)), x)

#===============================================================================
def sclk_split_count(count, delim=None):
    """Parse a spacecraft clock count into a list.

    Args:
        count (str): Number to convert.
        delim (str):
            Field delimiter to use. If None, all non-alphanumeric characters are
            treated as delimiters.


    Returns:
        list: Fields (int) of the given spacecraft clock count.
    """

    # Replace all non-alphanumerics with default delimiter if non given
    if delim is None:
        delim = '.'
        delims = list(set([c for c in count if not c.isalnum()]))
        table = {ord(d): ord(delim) for d in delims}
        count = count.translate(table)

    # Split the count string
    fields = list(map(int, (count.split(delim))))
    fields = fields + [0, 0, 0, 0]

    return fields[0:4]

#===============================================================================
def sclk_format_count(fields, format):
    """Construct a spacecraft clock count from a list of fields.

    Args:
        fields (list): Fields (int) the spacecraft clock count.
        format (str):
            Template indicating the fields widths and delimiters.  Alphanumeric
            characters indicate field digits, non-alphanumeric characters indicate
            field delimiters. Example: 'nnnnnnnn:nn:n.n'.

    Returns:
        int: Spacecraft clock count.
    """

    # Get delimiters
    delims = [c for c in format if not c.isalnum()] + ['']

    # Get field formats (i.e. field widths)
    f = "".join([s if s.isalnum() else '/' for s in format])
    formats = f.split('/')
    widths = [len(f) for f in formats]

    # Build count string
    count = ''
    for delim, width, field in zip(delims, widths, fields):
        s = f'{field}'
        count += '0'*(width-len(s)) + s + delim

    return count

#===============================================================================
def sclk_to_ticks(sclk, sc):
    """Convert spacecraft clock count string to ticks.

    Args:
        sclk (list): Spacecraft clock count string.
        sc (int): NAIF spacecraft identifier.

    Returns:
        int: Spacecraft clock ticks.
    """
    return cspyce.sctiks_alias(sc, sclk)

#===============================================================================
def get_observation_id(observation):
    """Utility function to determine the observation ID for an observation.

    Args:
        observation (oops.Observation): Observation object.

    Returns:
        str: Observation ID.
    """
    return str(observation.subfields['dict']['OBSERVATION_ID'])

#===============================================================================
def convert_mission_table(table, sc):
    """Convert mission table SCLK count string to ticks using sclk_to_ticks().

    Args:
        table (list): Systems table.
        sc (int): NAIF spacecraft identifier.

    Returns:
        list: Converted mission table containing ticks instead of strings.
    """
    new_table = []
    for item in table:
        new_table.append(
            ((sclk_to_ticks(item[1][0], sc),
              sclk_to_ticks(item[1][1], sc)),
              item[2], item[3], item[4], item[5], item[6]))

    return new_table

################################################################################
