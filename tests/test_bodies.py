################################################################################
# Body registry unit tests
################################################################################
"""The body registry holds each planet with its regular and extra children."""
import types
from typing import Any

import oops
import pytest

import metadata_tools.bodies as bodies_mod
import metadata_tools.config as cfg
import metadata_tools.defs as defs


def _fake_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the oops Body lookup with a small fake solar system."""
    registry: dict[str, Any] = {}

    def _body(name: str, parent: Any = None) -> Any:
        body = types.SimpleNamespace(name=name, parent=parent, regular=[])
        body.select_children = lambda kind: list(body.regular)
        registry[name] = body
        return body

    saturn = _body('SATURN')
    saturn.regular = [_body('MIMAS', saturn), _body('TITAN', saturn)]
    _body('PHOEBE', saturn)
    jupiter = _body('JUPITER')
    jupiter.regular = [_body('IO', jupiter)]
    _body('HIMALIA', jupiter)
    _body('MASURSKY', _body('SUN'))
    monkeypatch.setattr(oops.Body, 'lookup', staticmethod(lambda name: registry[name]))


def test_registry_holds_only_regular_children_by_default(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """With no extra children, an irregular moon is left out."""
    _fake_bodies(monkeypatch)
    assert list(bodies_mod.get_bodies(['JUPITER', 'SATURN'])) == [
        'JUPITER', 'IO', 'SATURN', 'MIMAS', 'TITAN']


def test_extra_children_follow_the_regular_children_of_their_planet(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """An extra child is registered with its siblings, whatever order it is listed in."""
    _fake_bodies(monkeypatch)
    assert list(bodies_mod.get_bodies(['JUPITER', 'SATURN'], ['PHOEBE', 'HIMALIA'])) == [
        'JUPITER', 'IO', 'HIMALIA', 'SATURN', 'MIMAS', 'TITAN', 'PHOEBE']


@pytest.mark.parametrize('name', ['MASURSKY', 'SUN'])
def test_extra_child_must_belong_to_a_registered_planet(
        monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    """A body that is no child of a registered planet is refused."""
    _fake_bodies(monkeypatch)
    with pytest.raises(ValueError, match=f'{name} is not a child of any of JUPITER, SATURN'):
        bodies_mod.get_bodies(['JUPITER', 'SATURN'], [name])


def test_registry_is_built_once_for_each_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each host gets its own registry, built with its own extra children."""
    _fake_bodies(monkeypatch)
    monkeypatch.setattr(bodies_mod, '_BODIES', {})
    monkeypatch.setattr(defs, 'BODY_NAMES', ['SATURN'])
    host = ['A']
    extras = {'A': [], 'B': ['PHOEBE']}
    monkeypatch.setattr(cfg, 'current_host_id', lambda: host[0])
    monkeypatch.setattr(cfg, 'get_extra_children', lambda: extras[host[0]])
    first = bodies_mod.get_bodies_registry()
    assert list(first) == ['SATURN', 'MIMAS', 'TITAN']
    assert bodies_mod.get_bodies_registry() is first
    host[0] = 'B'
    assert list(bodies_mod.get_bodies_registry()) == ['SATURN', 'MIMAS', 'TITAN', 'PHOEBE']
