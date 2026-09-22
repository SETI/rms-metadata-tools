################################################################################
# tests/columns/test_catalog.py: Invariants of the geometry column catalogs.
################################################################################
"""Hermetic tests for the body, ring, sky, and sun column catalogs.

The catalogs import nothing from oops or SPICE -- they are static descriptions
of how to compute each column -- so these run without a host or kernels.

These guard the catalog in isolation. That it agrees with the shipped label
templates is a separate question, checked in ``tests/test_geometry_schema.py``.
"""

import pytest

import metadata_tools.defs as defs
from metadata_tools.columns.catalog import (
    ColumnSpec,
    get_catalog,
    minmax,
    name_map,
    pair,
    single,
)

QUALIFIERS = ('body', 'ring', 'sky', 'sun')

# The number of values each catalog produces, i.e. the number of data columns a
# template may draw on. Pinned so an accidental addition or deletion is visible.
EXPECTED_VALUES = {'body': 51, 'ring': 81, 'sky': 4, 'sun': 30}


#===============================================================================
# Structural invariants, checked for every catalog
#===============================================================================
@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_names_match_value_count(qualifier: str) -> None:
    """Every spec names exactly as many columns as it produces values."""
    for spec in get_catalog(qualifier):
        assert len(spec.names) == spec.number_of_values
        assert spec.number_of_values in (1, 2)


@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_names_are_unique_within_a_catalog(qualifier: str) -> None:
    """No two specs claim the same NAME, so a template reference is unambiguous."""
    names = [name for spec in get_catalog(qualifier) for name in spec.names]
    assert len(names) == len(set(names))
    # name_map raises on a duplicate, so a clean build is itself the assertion.
    assert len(name_map(qualifier)) == len(names)


@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_value_count_is_pinned(qualifier: str) -> None:
    """The catalog's total value count matches the shipped templates."""
    total = sum(spec.number_of_values for spec in get_catalog(qualifier))
    assert total == EXPECTED_VALUES[qualifier]


@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_overflow_and_link_are_well_formed(qualifier: str) -> None:
    """Each spec's overflow format and link fields are self-consistent."""
    for spec in get_catalog(qualifier):
        assert spec.overflow_format is None or spec.overflow_format.startswith('%')
        # A link id and a link function only make sense together.
        assert bool(spec.link_id) == bool(spec.link)


@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_masks_are_well_formed(qualifier: str) -> None:
    """Each mask is (masker, shadower, face) drawn from the documented letters."""
    for spec in get_catalog(qualifier):
        masker, shadower, face = spec.mask
        assert set(masker) <= set('PRM')
        assert set(shadower) <= set('PRM')
        assert face in ('D', 'N', '')


#===============================================================================
# Placeholder substitution
#===============================================================================
def test_body_and_ring_keys_carry_the_placeholder() -> None:
    """Body and ring keys are written against BODYX, bound per body at add time."""
    for qualifier in ('body', 'ring'):
        assert any(defs.BODYX in str(spec.key) for spec in get_catalog(qualifier))


def test_sky_and_sun_keys_are_already_bound() -> None:
    """Sky and sun columns have no per-body variation, so no placeholder."""
    for qualifier in ('sky', 'sun'):
        assert not any(defs.BODYX in str(spec.key) for spec in get_catalog(qualifier))


def test_ring_diameter_key_holds_a_dict_reference() -> None:
    """The ring diameter key defers a RING_SYSTEM_RADII lookup to substitution time."""
    spec = name_map('ring')['RING_DIAMETER_IN_PIXELS'][0]
    assert 'RING_SYSTEM_RADII' in str(spec.key)


#===============================================================================
# Helpers
#===============================================================================
def test_minmax_builds_the_conventional_pair() -> None:
    """minmax derives MINIMUM_/MAXIMUM_ names from the stem."""
    spec = minmax('PHASE_ANGLE', ('phase_angle', 'IO'), ('', '', ''))
    assert spec.names == ('MINIMUM_PHASE_ANGLE', 'MAXIMUM_PHASE_ANGLE')


def test_single_builds_a_one_value_spec() -> None:
    """single names exactly one column."""
    spec = single('DIAMETER_IN_PIXELS', ('body_diameter_in_pixels', 'IO'), ('', '', ''))
    assert spec.names == ('DIAMETER_IN_PIXELS',)
    assert spec.number_of_values == 1


def test_name_map_rejects_a_duplicate_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two specs claiming one NAME is an error, not a silent last-wins."""
    clash = (minmax('PHASE_ANGLE', ('phase_angle', 'IO'), ('', '', '')),
             minmax('PHASE_ANGLE', ('center_phase_angle', 'IO'), ('', '', '')))
    monkeypatch.setattr('metadata_tools.columns.catalog.get_catalog',
                        lambda qualifier: clash)
    with pytest.raises(ValueError, match='duplicate column NAME'):
        name_map('body')


def test_column_spec_is_frozen() -> None:
    """A spec cannot be mutated, so a per-body binding cannot leak."""
    spec = get_catalog('body')[0]
    with pytest.raises(Exception):  # noqa: B017 - dataclasses raises FrozenInstanceError
        spec.key = ('other',)  # type: ignore[misc]


#===============================================================================
# What the spec still carries
#===============================================================================
def test_only_the_centre_coordinates_are_linked() -> None:
    """The null link groups the centre coordinates and nothing else."""
    linked = {name
              for qualifier in QUALIFIERS for spec in get_catalog(qualifier)
              for name in spec.names
              if spec.link_id}
    assert linked == {'CENTER_X_COORDINATE', 'CENTER_Y_COORDINATE',
                      'RING_CENTER_X_COORDINATE', 'RING_CENTER_Y_COORDINATE'}


def test_linked_columns_share_a_group_within_a_qualifier() -> None:
    """Columns that go null together carry the same link id and function."""
    for qualifier in QUALIFIERS:
        groups = {(spec.link, spec.link_id) for spec in get_catalog(qualifier)
                  if spec.link_id}
        assert len(groups) <= 1, f'{qualifier} has several link groups: {groups}'


def test_spec_rejects_a_half_specified_link() -> None:
    """A link id without a function, or vice versa, is a construction error."""
    with pytest.raises(ValueError, match='must be given together'):
        ColumnSpec(('A',), ('k',), ('', '', ''), link_id=1)
    with pytest.raises(ValueError, match='must be given together'):
        ColumnSpec(('A',), ('k',), ('', '', ''), link='null')


def test_spec_defaults_are_inert() -> None:
    """A spec that states nothing gets no overflow format and no link."""
    spec = minmax('PHASE_ANGLE', ('phase_angle', 'IO'), ('', '', ''))
    assert (spec.overflow_format, spec.link_id, spec.link) == (None, 0, '')


def test_the_catalog_states_no_conversion() -> None:
    """Conversion is derived from the label, so no spec carries a flag.

    This is the invariant the template pull rests on: the catalog says how to
    compute a column, the template says how to present it.
    """
    for qualifier in QUALIFIERS:
        for spec in get_catalog(qualifier):
            assert not hasattr(spec, 'flag')


def test_pair_builds_an_explicitly_named_two_value_spec() -> None:
    """pair names both halves outright, for FINEST_/COARSEST_ style columns."""
    spec = pair('FINEST_X', 'COARSEST_X', ('resolution', 'IO'), ('', '', ''))
    assert spec.names == ('FINEST_X', 'COARSEST_X')
    assert spec.number_of_values == 2


def test_catalog_specs_are_column_specs() -> None:
    """Each catalog is a tuple of ColumnSpec, not a list of raw tuples."""
    for qualifier in QUALIFIERS:
        catalog = get_catalog(qualifier)
        assert isinstance(catalog, tuple)
        assert all(isinstance(spec, ColumnSpec) for spec in catalog)


def test_get_catalog_rejects_an_unknown_qualifier() -> None:
    """A qualifier with no catalog is an error."""
    with pytest.raises(KeyError):
        get_catalog('asteroid')
