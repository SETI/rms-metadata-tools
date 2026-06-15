################################################################################
# util_textfiles.py: Text-file I/O helpers (split out of util.py).
#
# Re-exported by util.py so callers keep using `util.read_txt_file`, etc.
################################################################################
import os
import re
from pathlib import Path

from filecache import FCPath


#===============================================================================
def expandvars(filespec):           ### add to FCPath?
    """Expand environment variables in path.

    Args:
        filespec (str, Path, or FCPath): Path to expand.

    Returns:
        str, Path, or FCPath: Expanded path.

    """
    result = filespec
    if not isinstance(result, str):
        result = result.as_posix()

    result = re.sub('://', '<<token>>', result)
    result = os.path.expandvars(result)
    result = re.sub('<<token>>', '://', result)

    if isinstance(filespec, str):
        return result
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
    filespec = FCPath(filespec)

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
    filespec = FCPath(filespec)

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
def append_txt_file(filespec, content, terminator='\r\n'):    ### move to utilities
    """Append text to a file, with some options.

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
    filespec = FCPath(filespec)

    # Expand environment variables and resolve to absolute path
    filespec = expandvars(filespec)

    # If no file, just run write_txt_file().
    if not filespec.exists():
        write_txt_file(filespec, content, terminator=terminator)

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
    with open(Path(filespec.as_posix()), "a") as file:
        file.write(content)
