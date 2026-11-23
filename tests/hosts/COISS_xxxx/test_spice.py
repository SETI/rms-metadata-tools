################################################################################
# tests/hosts/COISS_xxxx/test_spice.py: Cassini ISS host with SPICE
################################################################################
"""The Cassini ISS mission table and body registry, checked against SPICE."""
import types

import cspyce
import julian
import pytest

import metadata_tools.bodies as bodies
from metadata_tools.config import get_geometry_config, set_host
from metadata_tools.geometry_support import bodies_select, formats

# These tests initialize the oops Cassini ISS host, which furnishes SPICE kernels
# (see the integration marker in pyproject.toml).
pytestmark = pytest.mark.integration

# The phase boundaries the mission table's comment documents, in UTC
PHASE_DATES = {
    'EARTH': ('1999-08-01T00:00:00', '1999-09-15T00:00:00'),
    'JUPITER': ('1999-09-16T00:00:00', '2002-07-11T00:00:00'),
    'SATURN': ('2002-07-12T00:00:00', '2017-09-16T00:00:00'),
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


@pytest.mark.parametrize(('sclk', 'primary'), [
    ('1308947812.000', ''),             # COISS_1001, last image before the Earth flyby
    ('1313413581.000', 'EARTH'),        # COISS_1001, Earth flyby
    ('1351738470.070', 'JUPITER'),      # COISS_1001, last image
    ('1404903617.118', 'JUPITER'),      # COISS_1007, last image
    ('1405160033.115', 'SATURN'),       # COISS_1008, first image
    ('1444749850.143', 'SATURN'),       # COISS_1009, first image
    ('1451040707.166', 'SATURN'),       # COISS_1009, last image
])
def test_cruise_volumes_have_the_primaries_of_the_earlier_release(sclk: str,
                                                                  primary: str) -> None:
    """Every image from the Earth flyby on has a primary, Jupiter through COISS_1007
    and Saturn from COISS_1008, as in the earlier release of these tables."""
    record = types.SimpleNamespace(observation=None)
    result = bodies_select.get_primary(record,                  # type: ignore[arg-type]
                                       formats.get_mission_table(), sclk)
    assert result[0] == primary


def test_cruise_kernels_give_pointing() -> None:
    """The cruise C kernels are furnished, so a cruise image has pointing.

    TEMPORARY: remove with the workaround in host_init.py once
    SETI/rms-host-cassini#42 is released.
    """
    from metadata_tools.hosts.COISS_xxxx import host_init
    assert len(host_init.CRUISE_CKS) == 31
    # W1444858008_1 (COISS_1009, 2003-10-14), covered only by 03274_04001rc.bc
    et = cspyce.scs2e(-82, '1444858005.077')
    rotation = cspyce.pxform('J2000', 'CASSINI_ISS_WAC', et)
    assert rotation.shape == (3, 3)


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
