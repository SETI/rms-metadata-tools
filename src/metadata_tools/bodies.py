################################################################################
# bodies.py: Build the oops Body registry used by the geometry column tables
################################################################################
"""Build the oops ``Body`` registry used by the geometry column tables."""
from collections.abc import Sequence
from typing import Any

import oops

import metadata_tools.config as hooks
import metadata_tools.defs as defs


def get_bodies(body_names: list[str], extra_children: Sequence[str] = ()) -> dict[str, Any]:
    """Build a registry mapping each body name to its oops ``Body`` object.

    For every name, the body itself and its regular children are included,
    followed by any of the extra children that are its own.

    Parameters:
        body_names: Names of the primary bodies to look up.
        extra_children: Names of irregular children of the primary bodies to
            treat exactly as their regular children are.

    Returns:
        Mapping from body name to the corresponding oops ``Body`` object,
        including each primary body's regular and extra children.

    Raises:
        ValueError: If an extra child is not a child of any primary body.
    """
    extras: dict[str, list[Any]] = {name: [] for name in body_names}
    for extra_name in extra_children:
        extra = oops.Body.lookup(extra_name)
        parent = extra.parent
        if parent is None or parent.name not in extras:
            raise ValueError(f'{extra.name} is not a child of any of {", ".join(body_names)}')
        extras[parent.name].append(extra)

    bodies: list[Any] = []
    for name in body_names:
        bod = oops.Body.lookup(name)
        bodies += [bod]
        bodies += bod.select_children('REGULAR')
        bodies += extras[name]
    return {body.name: body for body in bodies}


_BODIES: dict[str, dict[str, Any]] = {}


def get_bodies_registry() -> dict[str, Any]:
    """Return the active host's body registry, building it on the first call.

    Requires the host's oops module to have been initialized
    (e.g. ``SSI._initialize()`` in ``host_init.py``) before the first call.

    Returns:
        Mapping from body name to its oops ``Body`` object.
    """
    host_id = hooks.current_host_id()
    if host_id not in _BODIES:
        _BODIES[host_id] = get_bodies(defs.BODY_NAMES, hooks.get_extra_children())
    return _BODIES[host_id]
