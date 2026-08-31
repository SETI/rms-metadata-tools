################################################################################
# label_support.py - Tools for generating metadata labels.
################################################################################
"""Tools for generating PDS3 metadata labels from templates."""
from collections.abc import Callable
from pathlib import Path

from filecache import FCPath
from pdstemplate import PdsTemplate
from pdstemplate.pds3table import pds3_table_preprocessor

import metadata_tools.defs as defs
import metadata_tools.util as util


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

    # Default preprocessor
    preprocess: Callable[..., object] | None = pds3_table_preprocessor
    if 'inventory' in body:
        preprocess = None

    # Default template dictionary
    fields: dict[str, str] = {'VOLUME_ID'   : volume_id,
                              'TABLE_TYPE'  : table_type}

    # Generate label
    template = PdsTemplate(template_path, crlf=True,
                           preprocess=preprocess,
                           includes=[defs.GLOBAL_TEMPLATE_PATH, host_template_dir],
                           kwargs={'formats':True, 'numbers':True, 'validate':False})
    template.write(fields, label_path=label_path, mode='repair')

    return
################################################################################
