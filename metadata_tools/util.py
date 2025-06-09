################################################################################
# util.py: Utility functions
################################################################################
import os
import re
import numpy as np

from pathlib   import Path
from filecache import FCPath

import metadata_tools.defs as defs


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
def get_template_name(filename, volume_id):
    """Determine the name of the label template.

    Args:
        filename (str): Name of table or label file.

    Returns:
        str: Index name.
    """
    dir = Path.cwd()
    collection = dir.name
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

    return (host, index_type)

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
#    return path.split(volume_id)[-1]

#===============================================================================
def replace(tree, placeholder, name):
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

    new_tree = []
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
def replacement_dict(tree, placeholder, names):
    """Create a dictionary of copies of the tree of objects, where each
    dictionary entry is keyed by a name in the list and returns a copy of the
    tree using that name as the replacement.

    Args:
        tree (list): List contining the tree.
        placeholder (str): Placeholder to replace
        name (list): List of replacement strings.

    Returns:
        dict: New dictionary.

    """

    dict = {}
    for name in names:
        dict[name] = replace(tree, placeholder, name)

    return dict

#===============================================================================
def replacement_fn(dict, name):
    """Create a replacement-able dictionary reference.

    Args:
        dict (str): Name  of dictionary.
        name (str): Dictionary key, which could be a placeholder string.

    Returns:
        str: Dictionary reference keyed by possible placeholder name.

    """
    return dict + '["' + name + '"]'

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
def expandvars(filespec):           ### add to FCPath?
    """Expand environment variables in path.

    Args:
        filespec (str, Path, or FCPath): Path to expand.

    Returns:
        str, Path, or FCPath: Expanded path.

    """
    if not isinstance(filespec, str):
        result = filespec.as_posix()

    result = re.sub('://', '<<token>>', result)
    result = os.path.expandvars(result)
    result = re.sub('<<token>>', '://', result)

    if isinstance(filespec, str):
        return result.as_posix()
    if isinstance(filespec, FCPath):
        return FCPath(result)
    return Path(result)

#===============================================================================
def read_txt_file(filespec, as_string=False, terminator='\r\n'):    ### move to utilities
    """Read a text file, with some options.

    Args:
        filespec (str, Path, or FCPath):
            Path to the file to read.  Environment variables are expanded.
        as_string (bool, optional):
            If True, the result is returned as a string using the specified
            terminator.
        terminator (str): Terminator to use for string return.

    Returns:
        list (as_string==False): Lines of the file with no terminators.
        str (as_string==True): Lines of the file concatenated using the specified
        terminator.

    """

    # Expand environment variables and resolve to absolute path
    filespec = expandvars(filespec)

    # Read the file
    content = filespec.read_text(encoding='utf-8', newline=terminator)
    if as_string:
        return content

    # Split into list of lines with no terminator
    content = content.split('\n')
    if content[-1] == '':
        content = content[:-1]
    content = [c.rstrip('\r\n') for c in content]

    return content

#===============================================================================
def write_txt_file(filespec, content, terminator='\r\n'):    ### move to utilities
    """Write a text file, with some options.

    Args:
        filespec (str, Path, or FCPath): Path to the file to write.
        content (str or list):
            Text to write.  If list, each element is a line that will be terminated
            using the specified terminator.  If string, existing terminators are
            replaced with the specified terminator.
        terminator (str): Desired line terminator.

    Returns:
        None
    """

    # Expand environment variables and resolve to absolute path
    filespec = expandvars(filespec)

    # Determine terminator
    if terminator is None:
        if isinstance(content, list):
            crlf = content[0].endswith('\r\n')
        else:
            crlf = content.endswith('\r\n')
        terminator = '\r\n' if crlf else '\n'

    # Split into list of lines with no terminator
    if not isinstance(content, list):
        content = content.split('\n')
    content = [c.rstrip('\r\n') for c in content]

    # Reconstitute with correct terminator
    content = terminator.join(content) + terminator

    # Write file
    filespec.write_text(content, encoding='utf-8')

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
def sclk_to_ticks(sclk, bases):
    """Convert spacecraft clock count string to ticks.

    Args:
        sclk (list): Spacecraft clock count string.
        bases (list): Base (int) to use for each decimal place.

    Returns:
        int: Spacecraft clock ticks.
    """

    # Get fields
    fields = sclk_split_count(sclk)

    # Compute ticks
    ticks = fields[-1]
    for i in range(len(fields)-1):
        ticks += fields[i]*bases[i+1]

    return ticks

#===============================================================================
def convert_default_bodies_table(table, bases):
    """Convert default bodies tables SCLK count string to ticks.

    Args:
        table (list): Systems table.
        bases (list): Base (int) to use for each decimal place.

    Returns:
        list: Converted Systems table containing ticks instead of strings.
    """
    new_table = []
    for item in table:
        new_table.append(
            ((sclk_to_ticks(item[0][0], bases),
              sclk_to_ticks(item[0][1], bases)),
              item[1], item[2]))

    return new_table

#===============================================================================
def get_primary(table, sclk, bases):
    """Use converted default bodies table to determine the primary for a given
       spacecraft clock count.

    Args:
        table (list):
            Converted default bodies table containing sclk ticks instead of strings.
        sclk (str): Spacecraft clock string corresponding to the observation time.
        bases (list): Base (int) to use for each decimal place.

    Returns:
        NamedTuple (primary (str), secondaries (list)):
            primary: Name of the primary corresponding to the given SCLK value.
            secondaries:
                Names of any secondaries.
    """
    sclk_ticks = sclk_to_ticks(sclk, bases)
    for row in table:
        sclks = row[0]
        if sclk_ticks >= sclks[0] and sclk_ticks <= sclks[1]:
            return (row[1], row[2])
    return (None, None)

#===============================================================================
def range_of_n_angles(n, prob=0.1, tests=100000):
    """Used to study the statistics of n randomly chosen angles. This function
    was used to compute the NINETY_PERCENT_RANGE_DEGREES table below.

    For a set of n randomly chosen angles 0-360, return the interval such that the
    likelihood of all n angles falling within this interval of one another has the
    given probability. Base this on the specified number of tests.

    Args:
        n (int): Number of random samples to analyze.
        prob (float, optional): Probability criterion.
        tests (int, optional): Number of tests to perform.
    Returns:
        numpy.float64: Angular interval in degrees.
    """
    max_diffs = []
    for k in range(tests):
        values = np.random.rand(n) * 360.
        values = np.sort(values % 360)
        diffs = np.empty(values.size)
        diffs[:-1] = values[1:] - values[:-1]
        diffs[-1]  = values[0] + 360. - values[-1]
        max_diffs.append(diffs.max())

    max_diffs = np.sort(max_diffs)
    cutoff = int((1.-prob) * tests + 0.5)
    return 360. - max_diffs[cutoff]


################################################################################
# This is a tabulation of range_of_n_angles(N) for N in the range 0-1000
# We have 90% confidence that, if the N angles fall within this range, then the
# points do not sample a full 360 degrees of longitude.
################################################################################
NINETY_PERCENT_RANGE_DEGREES = np.array([
    0.000,   0.000,  18.000,  65.682, 105.260, 135.335, 158.717, 177.366, 192.527, 205.134,
  215.648, 225.089, 232.935, 239.913, 246.178, 251.693, 256.834, 261.349, 265.279, 269.092,
  272.471, 275.603, 278.550, 281.247, 283.765, 286.168, 288.339, 290.340, 292.325, 294.165,
  295.864, 297.473, 298.976, 300.490, 301.843, 303.207, 304.438, 305.556, 306.733, 307.824,
  308.847, 309.884, 310.841, 311.734, 312.588, 313.447, 314.264, 315.094, 315.822, 316.550,
  317.261, 317.970, 318.580, 319.220, 319.836, 320.457, 321.044, 321.560, 322.104, 322.608,
  323.119, 323.788, 324.007, 324.891, 325.153, 325.444, 325.846, 326.399, 326.476, 327.109,
  327.315, 327.836, 328.114, 328.482, 328.806, 329.285, 329.764, 329.890, 330.145, 330.617,
  330.905, 331.254, 331.386, 331.701, 332.006, 332.473, 332.484, 332.936, 333.199, 333.220,
  333.744, 333.740, 334.021, 334.347, 334.438, 334.794, 335.075, 335.232, 335.284, 335.611,
  335.909, 335.903, 336.214, 336.544, 336.682, 336.804, 336.868, 337.071, 337.370, 337.528,
  337.688, 337.753, 337.782, 338.255, 338.482, 338.519, 338.627, 338.681, 339.024, 339.043,
  339.346, 339.397, 339.602, 339.700, 339.894, 340.027, 340.092, 340.214, 340.468, 340.584,
  340.538, 340.687, 340.808, 341.034, 340.884, 341.211, 341.394, 341.394, 341.682, 341.751,
  341.812, 341.898, 342.161, 342.244, 342.359, 342.342, 342.426, 342.572, 342.702, 342.626,
  342.873, 343.100, 342.874, 343.032, 343.311, 343.285, 343.471, 343.518, 343.663, 343.694,
  343.727, 343.811, 344.054, 344.033, 344.099, 344.076, 344.212, 344.280, 344.473, 344.431,
  344.579, 344.582, 344.826, 344.849, 344.979, 344.987, 344.990, 345.085, 345.126, 345.149,
  345.264, 345.381, 345.464, 345.579, 345.546, 345.668, 345.718, 345.778, 345.800, 345.889,
  346.031, 345.977, 346.119, 346.129, 346.240, 346.259, 346.308, 346.400, 346.372, 346.454,
  346.527, 346.679, 346.624, 346.738, 346.772, 346.873, 346.938, 346.972, 347.079, 347.084,
  347.144, 347.174, 347.195, 347.298, 347.348, 347.385, 347.464, 347.477, 347.494, 347.526,
  347.618, 347.618, 347.743, 347.709, 347.852, 347.849, 347.970, 347.891, 348.000, 348.009,
  348.070, 348.135, 348.163, 348.210, 348.183, 348.348, 348.448, 348.324, 348.471, 348.483,
  348.515, 348.584, 348.621, 348.644, 348.651, 348.800, 348.774, 348.882, 348.885, 348.911,
  348.823, 348.969, 348.892, 348.970, 349.010, 349.121, 349.142, 349.193, 349.185, 349.329,
  349.318, 349.306, 349.408, 349.338, 349.416, 349.480, 349.479, 349.514, 349.616, 349.652,
  349.652, 349.621, 349.718, 349.735, 349.698, 349.778, 349.743, 349.888, 349.903, 349.864,
  349.951, 349.985, 349.937, 350.090, 350.021, 350.043, 350.226, 350.148, 350.174, 350.273,
  350.259, 350.245, 350.319, 350.264, 350.412, 350.421, 350.456, 350.414, 350.506, 350.563,
  350.593, 350.557, 350.614, 350.621, 350.620, 350.701, 350.669, 350.734, 350.754, 350.773,
  350.878, 350.850, 350.896, 350.863, 350.884, 350.942, 350.934, 351.004, 350.975, 351.065,
  351.036, 351.082, 351.087, 351.130, 351.167, 351.172, 351.161, 351.213, 351.284, 351.262,
  351.201, 351.353, 351.349, 351.336, 351.372, 351.395, 351.425, 351.426, 351.492, 351.507,
  351.555, 351.588, 351.578, 351.581, 351.631, 351.598, 351.621, 351.619, 351.692, 351.672,
  351.766, 351.699, 351.733, 351.759, 351.733, 351.830, 351.862, 351.907, 351.885, 351.869,
  351.982, 351.935, 351.999, 351.965, 352.035, 351.998, 352.025, 352.090, 352.072, 352.087,
  352.087, 352.122, 352.164, 352.123, 352.163, 352.143, 352.175, 352.218, 352.223, 352.352,
  352.307, 352.345, 352.352, 352.355, 352.346, 352.399, 352.362, 352.364, 352.445, 352.496,
  352.473, 352.485, 352.467, 352.530, 352.562, 352.551, 352.609, 352.619, 352.548, 352.652,
  352.612, 352.653, 352.671, 352.702, 352.767, 352.699, 352.759, 352.734, 352.752, 352.769,
  352.798, 352.759, 352.800, 352.862, 352.890, 352.900, 352.864, 352.949, 352.938, 352.921,
  352.975, 352.972, 352.977, 353.005, 352.975, 353.040, 352.997, 353.078, 353.059, 353.064,
  353.019, 353.110, 353.101, 353.141, 353.196, 353.161, 353.200, 353.176, 353.199, 353.178,
  353.252, 353.253, 353.271, 353.284, 353.272, 353.286, 353.321, 353.322, 353.331, 353.322,
  353.396, 353.328, 353.389, 353.370, 353.368, 353.411, 353.410, 353.460, 353.409, 353.483,
  353.475, 353.515, 353.497, 353.492, 353.573, 353.586, 353.509, 353.601, 353.585, 353.590,
  353.578, 353.574, 353.618, 353.645, 353.608, 353.674, 353.692, 353.696, 353.684, 353.697,
  353.701, 353.728, 353.733, 353.765, 353.785, 353.782, 353.777, 353.810, 353.779, 353.788,
  353.782, 353.835, 353.859, 353.864, 353.868, 353.875, 353.883, 353.922, 353.929, 353.952,
  353.937, 353.948, 353.981, 353.971, 353.933, 353.988, 354.019, 354.054, 354.000, 354.025,
  354.053, 354.067, 354.051, 354.050, 354.071, 354.076, 354.163, 354.124, 354.113, 354.122,
  354.145, 354.173, 354.168, 354.187, 354.199, 354.210, 354.252, 354.224, 354.232, 354.238,
  354.235, 354.219, 354.254, 354.283, 354.275, 354.265, 354.289, 354.317, 354.341, 354.318,
  354.366, 354.338, 354.330, 354.403, 354.339, 354.399, 354.377, 354.389, 354.405, 354.435,
  354.422, 354.420, 354.454, 354.463, 354.486, 354.481, 354.462, 354.485, 354.461, 354.508,
  354.520, 354.522, 354.513, 354.560, 354.523, 354.534, 354.585, 354.553, 354.572, 354.562,
  354.600, 354.564, 354.596, 354.642, 354.603, 354.625, 354.621, 354.640, 354.670, 354.661,
  354.686, 354.655, 354.701, 354.674, 354.680, 354.699, 354.731, 354.732, 354.742, 354.741,
  354.778, 354.776, 354.768, 354.767, 354.792, 354.820, 354.778, 354.798, 354.828, 354.844,
  354.826, 354.854, 354.850, 354.835, 354.868, 354.870, 354.888, 354.905, 354.871, 354.911,
  354.898, 354.902, 354.901, 354.974, 354.943, 354.951, 354.938, 354.973, 354.968, 354.979,
  354.997, 354.989, 355.002, 355.006, 355.038, 355.027, 355.043, 355.051, 354.994, 355.045,
  355.048, 355.048, 355.048, 355.059, 355.043, 355.104, 355.091, 355.122, 355.120, 355.099,
  355.099, 355.123, 355.155, 355.150, 355.118, 355.152, 355.176, 355.190, 355.124, 355.175,
  355.197, 355.170, 355.184, 355.256, 355.212, 355.236, 355.227, 355.221, 355.213, 355.260,
  355.277, 355.257, 355.278, 355.261, 355.280, 355.256, 355.309, 355.314, 355.290, 355.308,
  355.307, 355.331, 355.315, 355.336, 355.323, 355.335, 355.349, 355.376, 355.341, 355.400,
  355.357, 355.350, 355.366, 355.379, 355.398, 355.374, 355.409, 355.422, 355.406, 355.433,
  355.447, 355.447, 355.426, 355.459, 355.452, 355.475, 355.456, 355.471, 355.494, 355.496,
  355.483, 355.505, 355.495, 355.478, 355.517, 355.518, 355.530, 355.538, 355.551, 355.530,
  355.535, 355.572, 355.569, 355.543, 355.589, 355.555, 355.607, 355.586, 355.634, 355.578,
  355.604, 355.624, 355.616, 355.610, 355.629, 355.643, 355.629, 355.630, 355.634, 355.649,
  355.677, 355.650, 355.679, 355.658, 355.657, 355.690, 355.703, 355.686, 355.703, 355.694,
  355.714, 355.742, 355.729, 355.705, 355.721, 355.712, 355.741, 355.736, 355.768, 355.781,
  355.727, 355.758, 355.771, 355.794, 355.774, 355.794, 355.789, 355.772, 355.783, 355.807,
  355.804, 355.807, 355.828, 355.822, 355.838, 355.836, 355.820, 355.841, 355.840, 355.851,
  355.840, 355.857, 355.859, 355.889, 355.873, 355.887, 355.896, 355.876, 355.896, 355.936,
  355.896, 355.891, 355.934, 355.940, 355.934, 355.918, 355.927, 355.935, 355.921, 355.950,
  355.976, 355.998, 355.955, 355.937, 355.963, 355.984, 355.979, 355.969, 355.991, 355.980,
  355.994, 355.972, 355.999, 355.995, 355.989, 356.010, 356.025, 355.989, 356.038, 356.045,
  356.026, 356.042, 356.054, 356.038, 356.073, 356.058, 356.067, 356.074, 356.063, 356.077,
  356.091, 356.087, 356.116, 356.089, 356.103, 356.096, 356.124, 356.106, 356.126, 356.109,
  356.127, 356.101, 356.120, 356.132, 356.133, 356.141, 356.153, 356.162, 356.143, 356.142,
  356.167, 356.192, 356.168, 356.176, 356.170, 356.189, 356.167, 356.194, 356.188, 356.190,
  356.201, 356.189, 356.219, 356.216, 356.235, 356.233, 356.224, 356.218, 356.225, 356.257,
  356.248, 356.240, 356.244, 356.237, 356.261, 356.267, 356.293, 356.262, 356.275, 356.286,
  356.292, 356.293, 356.287, 356.306, 356.307, 356.297, 356.306, 356.300, 356.333, 356.310,
  356.329, 356.338, 356.302, 356.337, 356.314, 356.330, 356.336, 356.348, 356.335, 356.361,
  356.355, 356.377, 356.350, 356.389, 356.352, 356.380, 356.366, 356.378, 356.396, 356.382,
  356.402, 356.374, 356.381, 356.402, 356.406, 356.414, 356.390, 356.430, 356.424, 356.428,
  356.429, 356.440, 356.445, 356.441, 356.450, 356.463, 356.461, 356.439, 356.448, 356.462,
  356.451, 356.479, 356.471, 356.449, 356.495, 356.476, 356.486, 356.473, 356.479, 356.518,
  356.494, 356.492, 356.507, 356.494, 356.509, 356.513, 356.544, 356.509, 356.511, 356.504,
  356.517, 356.541, 356.526, 356.527, 356.542, 356.536, 356.553, 356.548, 356.553, 356.537,
  356.534, 356.557, 356.587, 356.563, 356.583, 356.588, 356.593, 356.582, 356.611, 356.583,
  356.589, 356.604, 356.585, 356.569, 356.598, 356.615, 356.598, 356.620, 356.624, 356.624,
  356.620, 356.625, 356.644, 356.627, 356.630, 356.651, 356.637, 356.640, 356.666, 356.651,
  356.661, 356.664, 356.679, 356.655, 356.638, 356.659, 356.674, 356.681, 356.672, 356.675,
  356.677, 356.687, 356.691, 356.685, 356.701, 356.712, 356.701, 356.696, 356.703, 356.717,
])

#===============================================================================
def _ninety_percent_gap_degrees(n):
    """For n samples, determine the approximate number of degrees for the largest
    gap in coverage providing 90% confidence that the angular coverage is not
    actually complete.

    Args:
        n (int): Number of samples.

    Returns:
        float: Estimated number of degrees.
    """

    # Below 1000, use the tabulation
    if n < 1000:
        return 360. - NINETY_PERCENT_RANGE_DEGREES[n]

    # Otherwise, this empirical fit does a good job
    return 1808. * n**(-0.912)

#===============================================================================
def _get_range_mod360(values, alt_format=None):
    """Determines the minimum and maximum values in the array, allowing for the
    possibility that the numeric range wraps around from 360 to 0.

    Args:
        values (list or np.array): The set of values for which to determine the range.
        alt_format (str, optional):
            "-180" to return values in the range (-180,180) rather
            than (0,360).

    Returns:
        list: Minimum and maximum values in the cyclic array.
    """

    # Check for use of negative values
    use_minus_180 = (alt_format == "-180")

    complete_coverage = [-180., 180.] if use_minus_180 else [0., 360.]

    # Flatten the set of values
    values = np.asarray(values.flatten().vals)

    # With only one value, we know nothing
    if values.size <= 1:
        return [values, values]

    # Locate the largest gap in coverage
    values = np.sort(values % 360)
    diffs = np.empty(values.size)
    diffs[:-1] = values[1:] - values[:-1]
    diffs[-1] = values[0] + 360. - values[-1]

    # Locate the largest gap and use it to define the range
    gap_index = np.argmax(diffs)
    diff_max = diffs[gap_index]
    range_mod360 = [values[(gap_index + 1) % values.size], values[gap_index]]

    # Convert to range -180 to 180 if necessary
    if use_minus_180:
        (lower, upper) = range_mod360
        lower = (lower + 180.) % 360. - 180.
        upper = (upper + 180.) % 360. - 180.
        range_mod360 = [lower, upper]

    # We want 90% confidence that the coverage is not complete. Otherwise,
    # return the complete range
    if diff_max >= _ninety_percent_gap_degrees(values.size):
        return range_mod360
    else:
        return complete_coverage
