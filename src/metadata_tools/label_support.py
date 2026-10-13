################################################################################
# label_support.py - Tools for generating metadata labels.
################################################################################
"""Tools for generating PDS3 metadata labels from templates."""
import csv
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from filecache import FCPath
from pdstemplate import PdsTemplate
from pdstemplate.pds3table import pds3_table_preprocessor

import metadata_tools.config as hooks
import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.column_grammar import (
    PRIVATE_KEYWORDS,
    RETIRED_KEYWORDS,
    expand_format_references,
    merge_column_definitions,
    strip_comments,
)

# The spec keywords carrying the geometry computation, from the grammar both
# paths share. They are not PDS3 Data Dictionary keywords, so they must never
# reach a shipped label. merge_column_definitions already keeps them out of
# merged columns; this line-level strip is the belt-and-braces for one written
# directly on a plain COLUMN. Retired grammar is swept up for free.
# The line-start anchor matches the schema reader's, so the read and strip can
# never disagree about what is a keyword line.
_PRIVATE_KEYWORD_RE = re.compile(
    r'^ *(' + '|'.join(PRIVATE_KEYWORDS + RETIRED_KEYWORDS) + r') *=[^\n]*\n',
    re.MULTILINE)


#===============================================================================
def _strip_private_keywords(template_path: object, content: str) -> str:
    """Remove the spec keywords from a template's content.

    Runs as a PdsTemplate preprocessor after ``pds3_table_preprocessor``.

    Parameters:
        template_path: The template path, unused; part of the preprocessor
            call signature.
        content: The template content, with LF line terminators.

    Returns:
        The content with every spec keyword line removed.
    """
    return _PRIVATE_KEYWORD_RE.sub('', content)


#===============================================================================
def _pds3_table_preprocessor(template_path: object, content: str) -> str:
    """Run rms-pdstemplate's PDS3 table preprocessor with our fixed options.

    A named wrapper because PdsTemplate hands its ``kwargs`` to the first
    preprocessor only, and ``strip_comments``, ``expand_format_references``,
    and ``merge_column_definitions`` must run first: the table preprocessor has
    to see the expanded, lowered, plain-COLUMN form.

    Parameters:
        template_path: The template path.
        content: The template content.

    Returns:
        The preprocessed content.
    """
    return str(pds3_table_preprocessor(template_path, content,
                                       formats=True, numbers=True, validate=False))


#===============================================================================
class HostTemplate(PdsTemplate):
    """A label template whose ``$INCLUDE`` files are sought in the host's directory first.

    PdsTemplate looks for an included file beside the template that includes
    it before anywhere else. That suits a template of the host's own, but the
    shared templates sit beside the shared column fragments, which would then
    always win. Searching the ``includes`` directories first, in the order
    given, lets a host shadow any shared fragment with a copy of its own
    whichever template includes it.
    """

    def _include_dirs(self) -> list[FCPath]:
        """Ordered list of all include directories to search."""
        dirs: list[FCPath] = list(self._includes)
        dirs += [d for d in super()._include_dirs() if d not in dirs]
        return dirs


#===============================================================================
def _border_text() -> str | None:
    """Word the border the host allows around a field of view.

    Returns:
        The border as an angle; None if the host allows no border.
    """
    border = hooks.get_border()
    if not border:
        return None
    return f'{border * 1000:g} milliradians'

#===============================================================================
def _inventory_field_bytes(filepath: FCPath, volume_id: str) -> tuple[int, int]:
    """Measure the fixed-width fields that begin each row of an inventory table.

    Every row begins with the volume ID and the file specification, the latter
    padded to the width of the host's FILE_SPECIFICATION_NAME column. The widths
    are read from the first row, so the label describes the table as written.

    Parameters:
        filepath: Path to the inventory table.
        volume_id: The table's volume ID.

    Returns:
        A tuple of the widths in bytes of the VOLUME_ID and
        FILE_SPECIFICATION_NAME fields. For a table with no complete first row,
        the width of the volume ID and zero.
    """
    with filepath.open('r', encoding='utf-8', newline='') as stream:
        row = next(csv.reader(stream), [])
    if len(row) < 2:
        return (len(volume_id), 0)
    return (len(row[0]), len(row[1]))


#===============================================================================
def create(filepath: str | Path | FCPath,
           host_template_path: str | Path | FCPath | None,
           *,
           table_type: str | None = '',
           fields: dict[str, Any] | None = None) -> None:
    """Create a PDS3 label for a metadata table.

    If filepath does not refer to an existing file, the function returns without
    writing anything.

    Parameters:
        filepath: Path to the local or remote table.
        host_template_path: Path to the host template, which locates the host's
            ``templates/`` directory. The label template is the host's own,
            named for the table, or else the one all hosts share; see
            :func:`metadata_tools.util.find_template`. If None, it is treated
            as an empty path.
        table_type: One of BODY_SUMMARY, RING_SUMMARY, SKY_SUMMARY,
            SUPPLEMENTAL_INDEX, or INVENTORY; case-insensitive (the value is
            uppercased). None is treated as an empty string.
        fields: Values for the template that only the caller knows: SAMPLING
            and BODY_SAMPLES, the pixel sampling density and the minimum
            number of samples across a body with which a geometry table was
            generated. A template is given None for one that is not stated.

    Raises:
        ValueError: If the table filename does not start with a volume id.
    """
    filepath = FCPath(filepath)
    if not filepath.is_file():
        return
    host_template_path = FCPath(host_template_path)
    table_type = (table_type or '').upper()

    # Get the label path
    filename = filepath.name
    parent_dir = filepath.parent
    body = filepath.stem
    label_path = parent_dir / (body + '.lbl')
    host_template_dir = host_template_path.parent

    # Get the volume id
    underscore = filename.find('_')
    if underscore < 0:
        raise ValueError(f'table filename {filename!r} does not start with a volume id')
    volume_id = filename[:underscore + 5]

    # The host's own template, or else the one all hosts share
    template_name = util.get_template_name(filename, volume_id, host_template_dir.parent)
    template_path = util.find_template(host_template_dir, template_name)

    # Default preprocessors: remove the comment lines, expand the
    # format-dictionary references, lower the definition/stub grammar to plain
    # COLUMNs, run the PDS3 table preprocessor on the lowered form, then sweep
    # any stray spec keyword. The inventory template has no COLUMN objects, so
    # it takes only the comment strip.
    preprocess: list[Callable[..., object]] = [strip_comments,
                                                      expand_format_references,
                                                      merge_column_definitions,
                                                      _pds3_table_preprocessor,
                                                      _strip_private_keywords]
    if 'inventory' in body:
        preprocess = [strip_comments]

    # Default template dictionary
    fields = {'VOLUME_ID'   : volume_id,
              'TABLE_TYPE'  : table_type,
              'FOV_BORDER'  : _border_text(),
              'SAMPLING'    : None,
              'BODY_SAMPLES': None} | (fields or {})
    if 'inventory' in body:
        (fields['VOLUME_ID_BYTES'],
         fields['FILESPEC_BYTES']) = _inventory_field_bytes(filepath, volume_id)

    # Generate label
    template = HostTemplate(template_path, crlf=True,
                            preprocess=preprocess,
                            includes=[host_template_dir, defs.GLOBAL_TEMPLATE_PATH])
    template.write(fields, label_path=label_path, mode='repair')

    return
################################################################################
