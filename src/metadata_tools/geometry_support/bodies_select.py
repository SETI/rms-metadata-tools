################################################################################
# geometry_support/bodies_select.py - Body selection and primary lookup.
#
# Free functions taking an explicit `record` argument so they can be exercised
# without constructing a full SPICE-backed Record. Most access the record's
# state read-only; the inventory functions may set record.pointing_available.
################################################################################
"""Body visibility and selection utilities for geometry table generation."""
import re
from typing import TYPE_CHECKING, Any, cast

import oops

import metadata_tools.bodies as bodies_mod
import metadata_tools.common as com
import metadata_tools.util as util
from metadata_tools.config import get_geometry_config

if TYPE_CHECKING:
    from metadata_tools.geometry_support.record import Record


#===============================================================================
def inventory(record: 'Record', bodies: list[str] | dict[str, Any]) -> list[str]:
    """Obtain image inventory if possible.

    Parameters:
        record: The geometry record.
        bodies: Bodies to test.

    Returns:
        List of inventory bodies. An empty list is returned if the inventory
        cannot be computed; when the failure indicates missing pointing data,
        record.pointing_available is also set to False.

    Raises:
        AssertionError: Re-raised, after logging, when raised unexpectedly by the
            inventory computation; likewise for AttributeError, IndexError,
            KeyError, LookupError, TypeError, and ValueError.
    """
    return cast(list[str], _inventory(record, bodies) or [])

#===============================================================================
def bounding_boxes(record: 'Record',
                   bodies: list[str]) -> dict[str, tuple[Any, tuple[float, float]]]:
    """Obtain the bounding box of each body in the image, if possible.

    The boxes are located in the field of view of the record's meshgrid, which
    is not necessarily that of the observation: the two differ for an image
    that is a cut-out window of the full frame.

    Parameters:
        record: The geometry record.
        bodies: Bodies to test.

    Returns:
        Mapping from the name of each body that falls unobscured inside the
        field of view to its box: the (u,v) coordinates of its center and its
        (u,v) diameters, in pixels and unrounded. The mapping is empty if the
        inventory cannot be computed; when the failure indicates missing
        pointing data, record.pointing_available is also set to False.

    Raises:
        AssertionError: Re-raised, after logging, when raised unexpectedly by the
            inventory computation; likewise for AttributeError, IndexError,
            KeyError, LookupError, TypeError, and ValueError.
    """
    if not bodies:
        return {}
    full = cast(dict[str, dict[str, Any]],
                _inventory(record, bodies, return_type='full',
                           fov=record.meshgrid.fov) or {})
    return {name: (entry['center_uv'],
                   (float(entry['u_pixel_size']), float(entry['v_pixel_size'])))
            for name, entry in full.items() if entry['inside']}

#===============================================================================
def _inventory(record: 'Record', bodies: list[str] | dict[str, Any],
               **kwargs: Any) -> Any:
    """Call the observation's inventory, handling missing pointing data.

    Parameters:
        record: The geometry record.
        bodies: Bodies to test.
        kwargs: Additional keyword arguments for the observation's inventory;
            by default it returns the list of body names.

    Returns:
        The inventory, or None if it cannot be computed; when the failure
        indicates missing pointing data, record.pointing_available is also set
        to False.

    Raises:
        AssertionError: Re-raised, after logging, when raised unexpectedly by the
            inventory computation; likewise for AttributeError, IndexError,
            KeyError, LookupError, TypeError, and ValueError.
    """
    logger = com.get_logger()

    # Attempt to obtain inventory
    try:
        try:
            return record.observation.inventory(
                bodies, expand=get_geometry_config().EXPAND, cache=False, **kwargs)
        except TypeError:
            # oops >= 0.3 dropped the cache option (removed in the src restructure)
            return record.observation.inventory(
                bodies, expand=get_geometry_config().EXPAND, **kwargs)

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
        return None

    # Other kinds of errors are genuine bugs.
    except (AssertionError, AttributeError, IndexError, KeyError,
            LookupError, TypeError, ValueError):
        logger.exception("Unexpected error during inventory")
        raise

#===============================================================================
def select_bodies(record: 'Record', bodies: dict[str, Any]) -> list[str]:
    """Select all bodies to include in this record.

    The selection follows these rules:

       1. The primary and secondary bodies are always included.
       2. Children of the primary are included if they intersect the FOV. If
          there are selections, then only the selected children are considered.
       3. If there is no primary, all selections that intersect the FOV are
          included.
       4. The target is included whenever it is registered with oops.
       5. If the target is a satellite, the parent is included.
       6. Additions are included whenever they intersect the FOV, regardless of
          the primary.

    Parameters:
        record: The geometry record.
        bodies: All bodies.

    Returns:
        List of selected bodies.
    """

    # Add bodies
    body_names = []

    # Add primary body and FOV/selected children
    if record.primary:
        body_names += [record.primary]
        registry = bodies_mod.get_bodies_registry()
        children = [child.name for child in registry[record.primary].children
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
        # A star target is registered by the oops host as a LightSource, which shares
        # the Body registry but belongs to no system and is not a body to select.
        system = get_system(record.target)
        if system:
            body_names += [system, record.target]

    # Cull duplicate bodies and verify all bodies are in the registry
    body_names = list(dict.fromkeys(body_names))

    # Sort bodies based on occurrence in BODIES list
    bodies_order = {name: i for i, name in enumerate(bodies_mod.get_bodies_registry())}
    body_names.sort(key=lambda name: bodies_order.get(name, len(bodies_order)))

    return [body_name for body_name in body_names if oops.Body.exists(body_name)]

#===============================================================================
def get_system(body: str) -> str | None:
    """Look up the system for a body.

    Parameters:
        body: Body for which to determine the system. For a satellite, the system
            is the parent. For a planet, the system is itself. For a root body
            with no parent (e.g. the Sun), the system is itself.

    Returns:
        Name of system, body, or None if the body is not registered or is registered
        as something other than a body (e.g. a star registered as a LightSource).
    """
    if body not in oops.Body.BODY_REGISTRY:
        return None
    entry = oops.Body.BODY_REGISTRY[body]
    if not hasattr(entry, 'parent'):
        return None
    parent_body = entry.parent
    # A root body such as the Sun has no parent; it is its own system.
    if parent_body is None:
        return body
    parent = parent_body.name
    if parent != 'SUN':
        return parent
    return body

#===============================================================================
def obs_excluded(record: 'Record', exceptions: list[str]) -> bool:
    """Determine whether an observation is excluded.

    Parameters:
        record: The geometry record.
        exceptions: List of exception specifiers. An entry that is a Python
            identifier names a geometry-config predicate function applied to
            the observation; any other entry is a regular expression tested
            against the observation ID.

    Returns:
        True if the observation is excluded.
    """
    if not exceptions:
        return False

    obs_id = util.get_observation_id(record.observation)
    for exception in exceptions:
        # An identifier names a config predicate function; anything else is a
        # regex tested against the observation ID. The observation is excluded if
        # *any* exception matches, so keep checking the remaining exceptions.
        if exception.isidentifier():
            fn = getattr(get_geometry_config(), exception)
            if fn(record.observation):
                return True
        elif re.match(exception, obs_id):
            return True

    return False

#===============================================================================
def get_primary(record: 'Record', table: list[Any],
                sclk: str) -> tuple[str, list[str], list[str], list[str]]:
    """Determine the primary for a given spacecraft clock count.

    Uses the converted default bodies table, which contains sclk ticks instead
    of strings.

    Parameters:
        record: The geometry record.
        table: Converted default bodies table containing sclk ticks instead of
            strings.
        sclk: Spacecraft clock string corresponding to the observation time.

    Returns:
        A tuple (primary, secondaries, selections, additions), where primary is
        the name of the primary corresponding to the given SCLK value,
        secondaries holds the names of any secondaries, selections holds the
        names of any selected bodies, and additions holds the names of any added
        bodies. If the observation is excluded or no table row spans the given
        SCLK value, ('', [], [], []) is returned.
    """
    fail: tuple[str, list[str], list[str], list[str]] = ('', [], [], [])
    sclk_ticks = util.sclk_to_ticks(sclk, get_geometry_config().SC)
    for row in table:
        if obs_excluded(record, row[1]):
            return fail
        sclks = row[0]
        if sclk_ticks >= sclks[0] and sclk_ticks <= sclks[1]:
            return (row[2], row[3], row[4], row[5])
    return fail
