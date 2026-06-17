################################################################################
# bodies.py: Build the oops Body registry used by the geometry column tables
################################################################################
"""Build the oops ``Body`` registry used by the geometry column tables."""
from typing import Any

import oops

import metadata_tools.defs as defs


def get_bodies(body_names: list[str]) -> dict[str, Any]:
    """Build a registry mapping each body name to its oops ``Body`` object.

    For every name, the body itself and its regular children are included.

    Parameters:
        body_names: Names of the primary bodies to look up.

    Returns:
        Mapping from body name to the corresponding oops ``Body`` object,
        including each primary body's regular children.
    """
    bodies: list[Any] = []
    for name in body_names:
        bod = oops.Body.lookup(name)
        bodies += [bod]
        bodies += bod.select_children('REGULAR')
    return {body.name: body for body in bodies}


# Computed once on import. This runs only after the host's oops module has been
# initialized (e.g. ssi.initialize() in host_init.py), because oops.Body.lookup
# requires the planetary bodies to be registered first.
BODIES = get_bodies(defs.BODY_NAMES)
"""Mapping from body name to its oops ``Body`` object, built once on import."""
