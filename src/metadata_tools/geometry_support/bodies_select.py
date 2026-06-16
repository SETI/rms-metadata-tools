################################################################################
# geometry_support/bodies_select.py - Body selection and primary lookup.
#
# Free functions taking an explicit `record` argument (read-only access to the
# record's state) so they can be exercised without constructing a full
# SPICE-backed Record.
################################################################################
import re

import geometry_config as config
import oops

import metadata_tools.columns as col
import metadata_tools.common as com
import metadata_tools.util as util


#===============================================================================
def inventory(record, bodies):
    """Obtain image inventory if possible.

    Args:
        record (Record): The geometry record.
        bodies (list): Bodies to test.

    Returns:
        List of inventory bodies.
    """
    logger = com.get_logger()

    # Attempt to obtain inventory
    try:
        inventory = record.observation.inventory(bodies, expand=config.EXPAND, cache=False)
        return inventory

    # A RuntimeError is probably caused by missing spice data. There is
    # probably nothing we can do.
    except (OSError, RuntimeError) as e:
        error = str(e)

        # If no C-kernel data for this observation, proceed with a warning and set the
        # pointing_available flag.
        if 'SPICE(NOFRAMECONNECT)' in error or 'SPICE(CKINSUFFDATA)' in error:
            logger.warning(str(e))
            record.pointing_available = False
        # Other kinds of errors are genuine bugs.
        else:
            logger.exception("Unexpected error during inventory")
        return []

    # Other kinds of errors are genuine bugs.
    except (AssertionError, AttributeError, IndexError, KeyError,
            LookupError, TypeError, ValueError):
        logger.exception("Unexpected error during inventory")
        return []

#===============================================================================
def select_bodies(record, bodies):
    """Select all bodies to include in this record according to the following rules:

       1. The primary and secondary bodies are always included.
       2. Children of the primary are included if they intersect the FOV. If there are
          selections, then only the selected children are considered.
       3. If there is no primary, all selections that intersect the FOV are included.
       4. The target is always included.
       5. If the target is a satellite, the parent is included.
       6. Additions are included whenever they intersect the FOV, regardless of the
          primary.

    Args:
        record (Record): The geometry record.
        bodies (list): All bodies.

    Returns:
        List of selected bodies.
    """

    # Add bodies
    body_names = []

    # Add primary body and FOV/selected children
    if record.primary:
        body_names += [record.primary]
        children = [child.name for child in col.BODIES[record.primary].children
                        if child.name in bodies]
        children = inventory(record, children)
        if record.selections:
            children = list(set(children) & set(record.selections))
        body_names += children
    # Add all FOV selections if no primary
    else:
        body_names += inventory(record, record.selections)

    # Add any secondary bodies
    if record.secondaries:
        body_names += record.secondaries

    # Add any additions in the FOV
    if record.additions:
        body_names += inventory(record, record.additions)

    # Add target body and parent
    if record.target and oops.Body.exists(record.target):
        system = get_system(record.target)
        if system:
            body_names += [system]
        body_names += [record.target]

    # Cull duplicate bodies and verify all bodies are in the registry
    body_names = list(dict.fromkeys(body_names))

    # Sort bodies based on occurrence in BODIES list
    body_names.sort(key=lambda name : list(col.BODIES.keys()).index(name))

    return [body_name for body_name in body_names if oops.Body.exists(body_name)]

#===============================================================================
def get_system(body):
    """Looks up the system for a body.

    Args:
        body (str): Body for which to determine the system.  For a satellite, the
                    system is the parent.  For planet, the system is itself.

    Returns:
        str: Name of system, body.
    """
    if body in oops.Body.BODY_REGISTRY:
        parent = oops.Body.BODY_REGISTRY[body].parent.name
    else:
        return None
    if parent != 'SUN':
        return parent
    return body

#===============================================================================
def obs_excluded(record, exceptions):
    """Use converted default bodies table to determine the primary for a given
       spacecraft clock count.

    Args:
        record (Record): The geometry record.
        exceptions (list): List of regular expressions to test against the observation ID.

    Returns:
        bool: True if the observation is excluded.
    """
    if not exceptions:
        return False

    obs_id = util.get_observation_id(record.observation)
    for exception in exceptions:
        # An identifier names a config predicate function; anything else is a
        # regex tested against the observation ID. The observation is excluded if
        # *any* exception matches, so keep checking the remaining exceptions.
        if exception.isidentifier():
            fn = getattr(config, exception)
            if fn(record.observation):
                return True
        elif re.match(exception, obs_id):
            return True

    return False

#===============================================================================
def get_primary(record, table, sclk):
    """Use converted default bodies table to determine the primary for a given
       spacecraft clock count.

    Args:
        record (Record): The geometry record.
        table (list):
            Converted default bodies table containing sclk ticks instead of strings.
        sclk (str): Spacecraft clock string corresponding to the observation time.

    Returns:
        NamedTuple (primary (str), secondaries (list), selections (list),
                    additions (list)):
            primary: Name of the primary corresponding to the given SCLK value.
            secondaries:
                Names of any secondaries.
            selections:
                Names of any selected bodies.
    """
    fail = ('', [], [], [])
    sclk_ticks = util.sclk_to_ticks(sclk, config.SC)
    for row in table:
        if obs_excluded(record, row[1]):
            return fail
        sclks = row[0]
        if sclk_ticks >= sclks[0] and sclk_ticks <= sclks[1]:
            return (row[2], row[3], row[4], row[5])
    return fail
