################################################################################
# tests/test_geometry_link_fns.py: link fields, helpers, and function lookup.
################################################################################
"""Tests for ``geometry_support.link_fns``."""
from collections.abc import Callable
from typing import Any

import pytest

from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support import link_fns
from metadata_tools.geometry_support.label_schema import ResolvedColumn
from metadata_tools.geometry_support.link_fns import LinkedField


#===============================================================================
# LinkedField
#===============================================================================
def test_a_numeric_field_is_null_by_value_not_text(make_stub: Callable[..., Any]) -> None:
    """A null is recognized however the field happens to be padded or formatted."""
    stub = make_stub(width=12, print_format='%12.3f', null_value=-9.99e9,
                     overflow_format='%12.5e')
    assert LinkedField(stub, '-9.99000e+09').is_null
    assert not LinkedField(stub, '       1.000').is_null


def test_a_string_field_is_null_inside_its_quotes(make_stub: Callable[..., Any]) -> None:
    """A string null matches the quoted, padded field the writer produces."""
    stub = make_stub(width=25, print_format='%25s', null_value='NA')
    assert LinkedField(stub, '"NA                     "').is_null
    assert not LinkedField(stub, '"2000-01-01T00:00:00.000"').is_null


def test_an_unparseable_numeric_field_is_not_null(make_stub: Callable[..., Any]) -> None:
    """A field that is not a number cannot be a numeric null."""
    assert not LinkedField(make_stub(), '"text"').is_null


def test_set_null_writes_the_formatted_null(make_stub: Callable[..., Any]) -> None:
    """The null is formatted like any value, overflow format included."""
    field = LinkedField(make_stub(width=12, print_format='%12.3f', null_value=-9.99e9,
                                  overflow_format='%12.5e'), '       1.000')
    field.set_null()
    assert field.text == '-9.99000e+09'
    assert field.is_null


#===============================================================================
# Helpers and shipped functions
#===============================================================================
def _group(make_stub: Callable[..., Any], *texts: str) -> link_fns.LinkGroup:
    """Build a group of 8-wide -999. fields named A, B, ... holding *texts*."""
    return {name: LinkedField(make_stub(name=name), text)
            for name, text in zip('ABCDEFG', texts, strict=False)}


def test_null_together_nulls_every_field(make_stub: Callable[..., Any]) -> None:
    """One null field nulls the whole group."""
    group = _group(make_stub, '   1.000', '-999.000', '   3.000')
    link_fns.null_together(group)
    assert [field.text for field in group.values()] == ['-999.000'] * 3


def test_null_together_leaves_a_complete_group(make_stub: Callable[..., Any]) -> None:
    """A group with no null is unchanged."""
    group = _group(make_stub, '   1.000', '   2.000')
    link_fns.null_together(group)
    assert [field.text for field in group.values()] == ['   1.000', '   2.000']


def test_the_centre_coordinates_null_together(make_stub: Callable[..., Any]) -> None:
    """LINK_CENTER_COORDINATE reports a centre whole or not at all."""
    group = _group(make_stub, '-999.000', '   2.000')
    link_fns.link_center_coordinate_fn(group)
    assert [field.text for field in group.values()] == ['-999.000', '-999.000']


#===============================================================================
# Lookup
#===============================================================================
def test_function_name_lowercases_and_appends_fn() -> None:
    """LINK_ID "LINK_CENTER_COORDINATE" calls link_center_coordinate_fn."""
    assert link_fns.function_name('LINK_CENTER_COORDINATE') == 'link_center_coordinate_fn'


def test_a_built_in_function_wins_over_the_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """As with index key functions, the built-in takes priority."""
    monkeypatch.setattr(get_geometry_config(), 'link_center_coordinate_fn',
                        lambda group: None, raising=False)
    assert (link_fns.find_link_function('LINK_CENTER_COORDINATE')
            is link_fns.link_center_coordinate_fn)


def test_the_host_supplies_a_function_the_built_ins_lack(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A LINK_ID with no built-in function falls back to the host's."""
    def link_host_fn(group: link_fns.LinkGroup) -> None:
        """A host-defined link function."""

    monkeypatch.setattr(get_geometry_config(), 'link_host_fn', link_host_fn,
                        raising=False)
    assert link_fns.find_link_function('LINK_HOST') is link_host_fn


def test_an_undefined_function_is_not_found() -> None:
    """Neither place defining it yields None."""
    assert link_fns.find_link_function('LINK_NOWHERE') is None


def test_a_non_callable_host_attribute_is_not_a_function(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Only a callable counts as a link function."""
    monkeypatch.setattr(get_geometry_config(), 'link_data_fn', 42, raising=False)
    assert link_fns.find_link_function('LINK_DATA') is None


#===============================================================================
# ResolvedColumn's link invariant
#===============================================================================
@pytest.mark.parametrize(('link_id', 'link_fn'), [('LINK_X', None),
                                                  ('', link_fns.null_together)])
def test_a_column_is_linked_by_id_and_function_together(
        link_id: str, link_fn: link_fns.LinkFunction | None) -> None:
    """An id without a function, or a function without an id, is rejected."""
    with pytest.raises(ValueError, match='needs both a link_id and a link_fn'):
        ResolvedColumn(key=('q', ()), mask=('', '', ''), link_id=link_id,
                       link_fn=link_fn)
