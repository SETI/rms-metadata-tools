################################################################################
# tests/hosts/COISS_xxxx/test_spice.py: Cassini ISS host with SPICE
################################################################################
"""The Cassini ISS mission table and body registry, checked against SPICE."""
import cspyce
import julian
import pytest

import metadata_tools.bodies as bodies
from metadata_tools.config import get_geometry_config, set_host

# These tests initialize the oops Cassini ISS host, which furnishes SPICE kernels
# (see the integration marker in pyproject.toml).
pytestmark = pytest.mark.integration

# The phase boundaries the mission table's comment documents, in UTC
PHASE_DATES = {
    'EARTH': ('1999-08-01T00:00:00', '1999-09-15T00:00:00'),
    'JUPITER': ('2000-10-01T00:00:00', '2001-03-31T00:00:00'),
    'SATURN': ('2004-01-01T00:00:00', '2017-09-16T00:00:00'),
}


@pytest.fixture(scope='module', autouse=True)
def cassini_host() -> None:
    """Make Cassini ISS the active host, initializing its oops host."""
    set_host('COISS_xxxx')
    get_geometry_config()


def _utc(sclk: str) -> str:
    """Return the UTC time, to the second, of a Cassini spacecraft clock count."""
    tdb = cspyce.scs2e(-82, sclk)
    return str(julian.iso_from_tai(julian.tai_from_tdb(tdb), digits=0)).rstrip('.')


def test_phase_clock_counts_fall_on_the_documented_dates() -> None:
    """Each phase begins and ends at midnight on the dates its comment gives."""
    for row in get_geometry_config().MISSION_TABLE:
        phase = row[0].strip()
        assert (_utc(row[1][0]), _utc(row[1][1])) == PHASE_DATES[phase], phase


@pytest.mark.parametrize(('moon', 'planet'), [('HIMALIA', 'JUPITER'),
                                              ('PHOEBE', 'SATURN')])
def test_extra_children_join_their_planets(moon: str, planet: str) -> None:
    """Himalia and Phoebe are registered as children of Jupiter and Saturn."""
    registry = bodies.get_bodies_registry()
    assert moon in registry
    assert registry[moon].parent.name == planet


def test_other_irregular_moons_are_left_out() -> None:
    """An irregular moon that is not named as an extra child is not registered."""
    registry = bodies.get_bodies_registry()
    assert 'ELARA' not in registry
    assert 'YMIR' not in registry
