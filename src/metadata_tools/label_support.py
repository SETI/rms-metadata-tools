################################################################################
# label_support.py - Tools for generating metadata labels.
################################################################################
"""Tools for generating PDS3 metadata labels from templates."""
import re
from collections.abc import Callable
from pathlib import Path

from filecache import FCPath
from pdstemplate import PdsTemplate
from pdstemplate.pds3table import pds3_table_preprocessor

import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.column_grammar import PRIVATE_KEYWORDS, merge_column_definitions

# The spec keywords carrying the geometry computation, from the grammar both
# paths share. They are not PDS3 Data Dictionary keywords, so they must never
# reach a shipped label. merge_column_definitions already keeps them out of
# merged columns; this line-level strip is the belt-and-braces for one written
# directly on a plain COLUMN. VALUES is retired grammar, swept up for free.
# The line-start anchor matches the schema reader's, so the read and strip can
# never disagree about what is a keyword line.
_PRIVATE_KEYWORD_RE = re.compile(
    r'^ *(' + '|'.join(PRIVATE_KEYWORDS + ('VALUES',)) + r') *=[^\n]*\n',
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
    preprocessor only, and ``merge_column_definitions`` must run first: the
    table preprocessor has to see the lowered, plain-COLUMN form.

    Parameters:
        template_path: The template path.
        content: The template content.

    Returns:
        The preprocessed content.
    """
    return str(pds3_table_preprocessor(template_path, content,
                                       formats=True, numbers=True, validate=False))


#===============================================================================
def create(filepath: str | Path | FCPath,
           host_template_path: str | Path | FCPath | None,
           system: str | None = None,
           *,
           use_global_template: bool = False,
           table_type: str | None = '') -> None:
    """Create a PDS3 label for a metadata table.

    If filepath does not refer to an existing file, the function returns without
    writing anything.

    Parameters:
        filepath: Path to the local or remote table.
        host_template_path: Path to the host template. If None, it is treated as
            an empty path; a real host template path is needed only when
            use_global_template is False.
        system: Name of system, for rings and moons.
        use_global_template: If True, the label template is to be found in the
            global template directory.
        table_type: One of BODY_SUMMARY, RING_SUMMARY, SKY_SUMMARY,
            SUPPLEMENTAL_INDEX, or INVENTORY; case-insensitive (the value is
            uppercased). None is treated as an empty string.
    """
    filepath = FCPath(filepath)
    if not filepath.is_file():
        return
    host_template_path = FCPath(host_template_path)
    table_type = (table_type or '').upper()

    # Get the label path
    if not system:
        system = ''
    filename = filepath.name
    parent_dir = filepath.parent
    body = filepath.stem
    label_path = parent_dir / (body + '.lbl')
    host_template_dir = host_template_path.parent

    # Get the volume id
    underscore = filename.index('_')
    volume_id = filename[:underscore + 5]

    # Default template path
    offset = 0 if not system else len(system) + 1
    if use_global_template:
        template_path = (FCPath(defs.GLOBAL_TEMPLATE_PATH) /
                         FCPath('%s.lbl' % body[underscore+6+offset:]))
    else:
        template_name = util.get_template_name(filename, volume_id, host_template_dir.parent)
        template_path = host_template_dir / (template_name + '.lbl')

    # Default preprocessors: lower the definition/stub grammar to plain
    # COLUMNs, run the PDS3 table preprocessor on the lowered form, then sweep
    # any stray spec keyword. The inventory template has no COLUMN objects, so
    # it takes none of them.
    preprocess: list[Callable[..., object]] | None = [merge_column_definitions,
                                                      _pds3_table_preprocessor,
                                                      _strip_private_keywords]
    if 'inventory' in body:
        preprocess = None

    # Default template dictionary
    fields: dict[str, str] = {'VOLUME_ID'   : volume_id,
                              'TABLE_TYPE'  : table_type}

    # Generate label
    template = PdsTemplate(template_path, crlf=True,
                           preprocess=preprocess,
                           includes=[defs.GLOBAL_TEMPLATE_PATH, host_template_dir])
    template.write(fields, label_path=label_path, mode='repair')

    return
################################################################################
