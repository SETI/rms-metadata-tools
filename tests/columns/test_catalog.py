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
    _format,
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
def test_every_spec_carries_a_format(qualifier: str) -> None:
    """Every spec resolved a format tuple, so no backplane key is unknown."""
    for spec in get_catalog(qualifier):
        flag, overflow, link_id, link = spec.format
        assert flag in ('', 'DEG', '360', '-180', 'ISO', 'KM')
        assert overflow is None or overflow.startswith('%')
        # A link id and a link function only make sense together.
        assert bool(link_id) == bool(link)


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
# Alternate formats
#===============================================================================
def test_alt_format_columns_differ_from_the_base_entry() -> None:
    """A column tagged with an alternate format resolves to the variant entry."""
    # Ring longitude relative to the observer uses the (-180, 180) convention,
    # unlike the other ring longitudes.
    wrt_observer = name_map('ring')['MINIMUM_RING_LONGITUDE_WRT_OBSERVER'][0]
    aries = name_map('ring')['MINIMUM_RING_LONGITUDE'][0]
    assert wrt_observer.format[0] == '-180'
    assert aries.format[0] == '360'


def test_km_alt_format_on_longitudinal_resolution() -> None:
    """The kilometre variant of the angular resolution resolves to the KM entry."""
    spec = name_map('ring')['FINEST_LONGITUDINAL_RESOLUTION_KM'][0]
    assert spec.format[0] == 'KM'


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
# The inline format fields
#===============================================================================
@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_format_fields_are_well_formed(qualifier: str) -> None:
    """Each spec's inline format tuple holds the four documented fields."""
    for spec in get_catalog(qualifier):
        assert len(spec.format) == 4
        flag, overflow, link_id, link = spec.format
        assert flag in ('', 'DEG', '360', '-180', 'ISO', 'KM')
        assert overflow is None or overflow.startswith('%')
        assert isinstance(link_id, int)
        assert isinstance(link, str)


def test_only_the_centre_coordinates_are_linked() -> None:
    """The null link groups the centre coordinates and nothing else."""
    linked = {name
              for qualifier in QUALIFIERS for spec in get_catalog(qualifier)
              for name in spec.names
              if spec.format[2]}
    assert linked == {'CENTER_X_COORDINATE', 'CENTER_Y_COORDINATE',
                      'RING_CENTER_X_COORDINATE', 'RING_CENTER_Y_COORDINATE'}


def test_linked_columns_share_a_group_within_a_qualifier() -> None:
    """Columns that go null together carry the same link id and function."""
    for qualifier in QUALIFIERS:
        groups = {spec.format[2:4] for spec in get_catalog(qualifier) if spec.format[2]}
        assert len(groups) <= 1, f'{qualifier} has several link groups: {groups}'


def test_format_rejects_a_half_specified_link() -> None:
    """A link id without a function, or vice versa, is a construction error."""
    with pytest.raises(ValueError, match='must be given together'):
        _format('', None, 1, '')
    with pytest.raises(ValueError, match='must be given together'):
        _format('', None, 0, 'null')


def test_format_defaults_to_no_conversion_and_no_link() -> None:
    """A spec that states nothing gets the inert format tuple."""
    spec = minmax('PHASE_ANGLE', ('phase_angle', 'IO'), ('', '', ''))
    assert spec.format == ('', None, 0, '')


def test_inline_flags_replace_the_old_alt_format_keying() -> None:
    """A variant column states its own flag rather than carrying a lookup tag.

    These three used to need (quantity, tag) entries in a second dictionary,
    because one quantity had to yield two different conversions.
    """
    ring = name_map('ring')
    assert ring['MINIMUM_RING_LONGITUDE_WRT_OBSERVER'][0].format[0] == '-180'
    assert ring['MINIMUM_RING_LONGITUDE'][0].format[0] == '360'
    assert ring['FINEST_LONGITUDINAL_RESOLUTION_KM'][0].format[0] == 'KM'
    assert ring['FINEST_LONGITUDINAL_RESOLUTION'][0].format[0] == 'DEG'


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
