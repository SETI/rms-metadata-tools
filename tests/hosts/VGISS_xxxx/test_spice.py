################################################################################
# tests/hosts/VGISS_xxxx/test_spice.py: Voyager ISS host with SPICE
################################################################################
"""The Voyager ISS mission table and body registry, checked against the oops host."""
import pytest

import metadata_tools.bodies as bodies
from metadata_tools.config import get_geometry_config, set_host
from metadata_tools.geometry_support import formats

# These tests initialize the oops Voyager ISS host, which furnishes SPICE kernels
# (see the integration marker in pyproject.toml).
pytestmark = pytest.mark.integration

pytest.importorskip('host_voyager.oops', reason='rms-host-voyager is not installed')


@pytest.fixture(scope='module', autouse=True)
def voyager_host() -> None:
    """Make Voyager ISS the active host, initializing its oops host."""
    set_host('VGISS_xxxx')
    get_geometry_config()


def test_mission_table_resolves_to_time_ranges() -> None:
    """The engine resolves every row to a time range, with no spacecraft ID."""
    table = formats.get_mission_table()
    assert [row[2] for row in table] == ['JUPITER', 'SATURN', 'URANUS', 'NEPTUNE']
    assert {row[0].key for row in table} == {'TIME'}


@pytest.mark.parametrize(('moon', 'planet'), [('HIMALIA', 'JUPITER'),
                                              ('PHOEBE', 'SATURN'),
                                              ('NEREID', 'NEPTUNE'),
                                              ('TRITON', 'NEPTUNE')])
def test_moons_join_their_planets(moon: str, planet: str) -> None:
    """The extra children, and Triton, are registered as children of their planets."""
    registry = bodies.get_bodies_registry()
    assert moon in registry
    assert registry[moon].parent.name == planet


def test_selected_moons_are_registered() -> None:
    """Every moon the mission table selects is in the body registry."""
    registry = bodies.get_bodies_registry()
    config = get_geometry_config()
    for planet in ('JUPITER', 'SATURN', 'URANUS', 'NEPTUNE'):
        missing = set(getattr(config, planet + '_MOONS')) - set(registry)
        assert not missing, (planet, missing)
