################################################################################
# label_support.py - Tools for generating metadata labels.
################################################################################
from filecache             import FCPath
from pdstemplate           import PdsTemplate
from pdstemplate.pds3table import pds3_table_preprocessor

import metadata_tools as meta
import metadata_tools.util as util
import metadata_tools.defs as defs

#===============================================================================
def create(filepath, system=None,
                     use_global_template=False,
                     table_type=''):
    """Creates a label for a given geometry table.

    Args:
        filepath (str|Path|FCPath): Path to the local or remote geometry table.
        system (str): Name of system, for rings and moons.
        use_global_template (bool):
            If True, the label template is to be found in the global template
        table_type (str, optional): BODY, RING, SKY, SUPPLEMENTAL_INDEX, INVENTORY.

    Returns:
        None.
    """
    filepath = FCPath(filepath)
    if not filepath.exists():
        return
    table_type = table_type.upper()

    # Get the label path
    if not system:
        system = ''
    filename = filepath.name
    dir = filepath.parent
    body = filepath.stem
    label_path = dir / (body + '.lbl')

    # Get the volume id
    underscore = filename.index('_')
    volume_id = filename[:underscore + 5]

    # Default template path
    offset = 0 if not system else len(system) + 1
    if use_global_template:
        template_path = FCPath(defs.GLOBAL_TEMPLATE_PATH) / FCPath('%s.lbl' % body[underscore+6+offset:])
    else:
        template_name = util.get_template_name(filename, volume_id)
        template_path = FCPath('./templates/').resolve() / (template_name + '.lbl')

    # Default preprocessor
    preprocess = pds3_table_preprocessor
    if 'inventory' in body:
        preprocess = None

    # Default template dictionary
    fields = {'VOLUME_ID'  : volume_id,
              'TABLE_TYPE' : table_type}

    # Generate label
    T = PdsTemplate(template_path, crlf=True,
                    preprocess=preprocess,
                    kwargs={'formats':True, 'numbers':True, 'validate':False})
    T.write(fields, label_path=label_path, mode='repair')

    return
################################################################################
