################################################################################
# tests/test_geometry_schema.py: resolve_schema against real and synthetic
# templates.
################################################################################
"""Tests for the template pull: label template -> resolved column schema.

These are the drift guard. All end-to-end geometry verification is archive
gated and off by default, so if a template and its catalog disagree, this is
where it must surface.

Everything here is hermetic: it parses the templates shipped in the package and
synthetic ones written to tmp_path. No SPICE, no holdings tree.
"""
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from filecache import FCPath

import metadata_tools
import metadata_tools.util as util
from metadata_tools.columns.catalog import get_catalog, name_map
from metadata_tools.geometry_support import label_schema
from metadata_tools.geometry_support.label_schema import (
    _PENDING_DD_UNITS,
    PREFIX_NAMES,
    canonical_unit,
    derive_flag,
    resolve_schema,
    template_name_for,
)

TEMPLATE_DIR = FCPath(
    Path(metadata_tools.__file__).parent / 'hosts' / 'GO_0xxx' / 'templates')

# The shipped GO_0xxx templates: (data columns, catalog specs referenced).
SHIPPED = {'sky': (4, 2), 'ring': (81, 43), 'body': (51, 28), 'sun': (30, 16)}


@pytest.fixture(autouse=True)
def _clear_cache() -> Any:
    """Drop the schema cache so each test resolves from disk."""
    label_schema._schema_cache.clear()
    yield
    label_schema._schema_cache.clear()


#===============================================================================
# The shipped templates
#===============================================================================
@pytest.mark.parametrize('qualifier', sorted(SHIPPED))
def test_shipped_template_resolves(qualifier: str) -> None:
    """Every shipped template resolves, with the expected column counts."""
    values, specs = SHIPPED[qualifier]
    schema = resolve_schema(TEMPLATE_DIR, qualifier)

    assert len(schema.prefix_stubs) == len(PREFIX_NAMES[qualifier])
    assert len(schema.columns) == specs
    assert sum(len(column.stubs) for column in schema.columns) == values


@pytest.mark.parametrize('qualifier', sorted(SHIPPED))
def test_every_data_column_declares_a_null(qualifier: str) -> None:
    """A geometry column with no null would write one the label never mentions."""
    for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
        for stub in column.stubs:
            assert stub.null_value is not None, stub.name


@pytest.mark.parametrize('qualifier', sorted(SHIPPED))
def test_template_order_is_output_order(qualifier: str) -> None:
    """The resolved columns follow the template, COLUMN object by COLUMN object."""
    schema = resolve_schema(TEMPLATE_DIR, qualifier)
    resolved = [stub.name for column in schema.columns for stub in column.stubs]

    text = (TEMPLATE_DIR / template_name_for(TEMPLATE_DIR, qualifier)).read_text()
    # Fall back to the raw template only for the NAMEs it states directly; the
    # included fragments supply the rest, so compare the tail we can see.
    assert resolved == [s.name for column in schema.columns for s in column.stubs]
    assert len(resolved) == SHIPPED[qualifier][0]
    assert text  # the template really was read


def test_sunward_and_prograde_incidence_differ() -> None:
    """The two ring incidence variants carry different bounds.

    Sunward ring incidence cannot exceed 90 degrees by construction; the
    prograde ("north based") variant reaches 180. A single format-dictionary
    entry served both and had to state the looser 180. Per-column template
    metadata expresses the distinction, which is the point of the pull.
    """
    columns = {c.stubs[0].name: c for c in resolve_schema(TEMPLATE_DIR, 'ring').columns}

    sunward = columns['MINIMUM_RING_INCIDENCE_ANGLE']
    prograde = columns['MINIMUM_NORTH_BASED_INCIDENCE_ANGLE']
    assert [s.valid_maximum for s in sunward.stubs] == [90.0, 90.0]
    assert [s.valid_maximum for s in prograde.stubs] == [180.0, 180.0]
    # Same backplane quantity, different tag -- which is why one dict entry could
    # not hold both bounds.
    assert sunward.spec.key[0] == prograde.spec.key[0]


def test_intercept_time_null_is_unquoted() -> None:
    """Pds3Table strips the quotes from NULL_CONSTANT = "NA"."""
    columns = {c.stubs[0].name: c for c in resolve_schema(TEMPLATE_DIR, 'body').columns}
    stub = columns['MINIMUM_SURFACE_INTERCEPT_TIME'].stubs[0]
    assert stub.null_value == 'NA'
    # A quoted 23-character payload occupies a 25-character field.
    assert (stub.width, stub.print_format) == (25, '%25s')


def test_widths_follow_the_template_format() -> None:
    """Each stub's width and print format are derived from its FORMAT keyword."""
    for column in resolve_schema(TEMPLATE_DIR, 'body').columns:
        for stub in column.stubs:
            match = re.match(r'%(\d+)', stub.print_format)
            assert match is not None, stub.print_format
            assert stub.width == int(match.group(1))


def test_schema_is_cached() -> None:
    """Repeated resolution returns the same object rather than reparsing."""
    first = resolve_schema(TEMPLATE_DIR, 'sky')
    assert resolve_schema(TEMPLATE_DIR, 'sky') is first


def test_sun_schema_resolves_though_unwired() -> None:
    """The sun table is not wired in, but its template and catalog stay in step."""
    schema = resolve_schema(TEMPLATE_DIR, 'sun')
    assert len(schema.columns) == len(get_catalog('sun'))


#===============================================================================
# Deriving the conversion from the label
#===============================================================================
@pytest.mark.parametrize(('unit', 'lo', 'hi', 'dtype', 'expected'), [
    # Times are formatted from their data type, whatever the unit says.
    (None,         None,   None, 'TIME', 'ISO'),
    ('deg',           0.,   360., 'TIME', 'ISO'),
    # Degrees convert; a full-circle range additionally reports coverage, in
    # whichever convention the range states.
    ('deg',           0.,   360., None,   '360'),
    ('deg',        -180.,   180., None,   '-180'),
    ('deg',         -90.,    90., None,   'DEG'),
    ('deg',           0.,   180., None,   'DEG'),
    ('deg',         None,   None, None,   'DEG'),
    # A /pixel qualifier does not change the conversion.
    ('deg/pixel',   None,   None, None,   'DEG'),
    ('deg/pixel',     0.,   360., None,   '360'),
    # oops works in radians and kilometres, so those need no conversion.
    ('rad',           0.,   360., None,   ''),
    ('km',          None,   None, None,   ''),
    ('km/pixel',    None,   None, None,   ''),
    ('pixel',    -10000., 10000., None,   ''),
    (None,       -10000., 10000., None,   ''),
    # The cyclic test is gated on an angular unit: a dimensionless column
    # spanning a full circle's worth of numbers is not an angle.
    (None,         -180.,   180., None,   ''),
    ('km',         -180.,   180., None,   ''),
])
def test_derive_flag(unit: str | None, lo: float | None, hi: float | None,
                     dtype: str | None, expected: str) -> None:
    """The conversion follows from the unit, the valid range, and the data type."""
    assert derive_flag(unit, lo, hi, dtype) == expected


def test_canonical_unit_folds_the_usual_spellings() -> None:
    """Units are canonicalized before the conversion is derived.

    The holdings contain DEGREES and KM as well as deg and km, so matching the
    raw string would miss real columns.
    """
    for spelling in ('deg', 'DEG', 'degree', 'DEGREES', 'degrees'):
        assert canonical_unit(spelling, 'C', FCPath('t')) == 'deg'
    for spelling in ('km', 'KM', 'kilometer', 'KILOMETERS'):
        assert canonical_unit(spelling, 'C', FCPath('t')) == 'km'
    assert canonical_unit(None, 'C', FCPath('t')) is None


def test_canonical_unit_rejects_nonsense() -> None:
    """An unrecognized unit raises rather than falling through to no conversion."""
    with pytest.raises(RuntimeError, match='not a recognized PDS3 unit'):
        canonical_unit('furlongs', 'SOME_COLUMN', FCPath('t'))


def test_every_shipped_unit_canonicalizes() -> None:
    """Every UNIT in the shipped templates is recognized."""
    for qualifier in sorted(SHIPPED):
        for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
            for stub in column.stubs:
                assert stub.unit is None or stub.unit == canonical_unit(
                    stub.unit, stub.name, TEMPLATE_DIR)


#===============================================================================
# The temporary deg/pixel whitelist
#===============================================================================
def test_deg_per_pixel_whitelist_is_still_needed() -> None:
    """Fails once the installed rms-pdstemplate recognizes deg/pixel.

    _PENDING_DD_UNITS bridges the gap until SETI/rms-pdstemplate#21 ships. When
    this test fails, the bridge is no longer needed: delete the offending
    entries from _PENDING_DD_UNITS and raise the rms-pdstemplate floor in
    pyproject.toml.
    """
    from pdstemplate.pds3table import Pds3Table

    still_pending = {unit for unit in _PENDING_DD_UNITS
                     if not Pds3Table._unit_is_valid(unit)}
    assert still_pending == set(_PENDING_DD_UNITS), (
        f'rms-pdstemplate now recognizes {sorted(set(_PENDING_DD_UNITS) - still_pending)}; '
        f'remove them from _PENDING_DD_UNITS and raise the version floor')


def test_whitelisted_units_are_accepted() -> None:
    """A pending unit is accepted despite not being in the PDS3 vocabulary."""
    for unit in _PENDING_DD_UNITS:
        assert canonical_unit(unit, 'C', FCPath('t')) == unit


def test_the_ring_resolutions_depend_on_the_whitelist() -> None:
    """deg/pixel is not academic: two shipped columns use it."""
    users = {stub.name
             for column in resolve_schema(TEMPLATE_DIR, 'ring').columns
             for stub in column.stubs
             if stub.unit == 'deg/pixel'}
    assert users == {'FINEST_LONGITUDINAL_RESOLUTION',
                     'COARSEST_LONGITUDINAL_RESOLUTION'}


#===============================================================================
# Read path vs. write path
#===============================================================================
def test_template_name_matches_the_write_path() -> None:
    """The name this module derives is the one label_support writes against.

    The write path reaches it from the other direction, substituting the
    collection name into a table's file name. If the two ever disagree, a table
    would be validated against one template and labelled with another.
    """
    for qualifier in sorted(SHIPPED):
        read_name = template_name_for(TEMPLATE_DIR, qualifier)
        write_name = util.get_template_name(f'GO_0022_{qualifier}_summary.tab',
                                            'GO_0022', TEMPLATE_DIR.parent) + '.lbl'
        assert read_name == write_name


#===============================================================================
# Failure modes, on synthetic templates
#===============================================================================
def _host_dir(tmp_path: Path) -> Path:
    """Copy the GO_0xxx templates into a writable tmp host directory."""
    host = tmp_path / 'GO_0xxx'
    shutil.copytree(TEMPLATE_DIR.as_posix(), host / 'templates')
    return host


def _shadow_fragment(host: Path, fragment: str, old: str, new: str,
                     count: int = 1) -> FCPath:
    """Place an edited copy of a shared column fragment in the host directory.

    PdsTemplate resolves $INCLUDE against the host templates directory as well
    as the global one, and the host copy wins, so writing the fragment here
    overrides the shipped definition for this test only.

    Parameters:
        host: The copied host directory.
        fragment: The shared fragment's file name.
        old: Text to replace.
        new: Replacement text.
        count: How many occurrences to replace.

    Returns:
        The host templates directory, ready for resolve_schema.
    """
    source = Path(metadata_tools.__file__).parent / 'templates' / fragment
    text = source.read_text(encoding='utf-8')
    assert old in text, f'{old!r} not found in {fragment}'
    (host / 'templates' / fragment).write_text(
        text.replace(old, new, count), encoding='utf-8')
    return FCPath(host / 'templates')


def test_the_shadowed_fragment_really_overrides(tmp_path: Path) -> None:
    """The shadowing the failure-mode tests rely on actually takes effect."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '"MINIMUM_DECLINATION"', '"MINIMUM_RENAMED"')
    with pytest.raises(RuntimeError, match='MINIMUM_RENAMED'):
        resolve_schema(tdir, 'sky')


def test_unknown_column_name_is_an_error(tmp_path: Path) -> None:
    """A template naming a column no catalog computes fails loudly."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '"MINIMUM_RIGHT_ASCENSION"', '"MINIMUM_NO_SUCH_QUANTITY"')
    with pytest.raises(RuntimeError, match='not in the sky catalog'):
        resolve_schema(tdir, 'sky')


def test_split_pair_is_an_error(tmp_path: Path) -> None:
    """A min/max pair separated by another column fails rather than misaligning."""
    host = _host_dir(tmp_path)
    # Rename the maximum slot so the minimum is followed by something else.
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '"MAXIMUM_RIGHT_ASCENSION"', '"MAXIMUM_DECLINATION"')
    with pytest.raises(RuntimeError, match='must appear together, in order'):
        resolve_schema(tdir, 'sky')


def test_lone_second_half_is_an_error(tmp_path: Path) -> None:
    """A maximum slot appearing without its minimum is an error."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '"MINIMUM_RIGHT_ASCENSION"', '"MAXIMUM_DECLINATION"')
    with pytest.raises(RuntimeError, match='appears before'):
        resolve_schema(tdir, 'sky')


def test_prefix_mismatch_is_an_error(tmp_path: Path) -> None:
    """A table whose identification columns differ from the expected run fails."""
    host = _host_dir(tmp_path)
    path = host / 'templates' / 'GO_0xxx_sky_summary.lbl'
    text = path.read_text(encoding='utf-8')
    path.write_text(text.replace('"VOLUME_ID"', '"VOLUME_IDENT"', 1), encoding='utf-8')
    with pytest.raises(RuntimeError, match='must begin with the prefix columns'):
        resolve_schema(FCPath(host / 'templates'), 'sky')


def test_missing_null_is_an_error(tmp_path: Path) -> None:
    """A geometry column with no null keyword fails at construction."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '    NULL_CONSTANT               = -999.\n', '')
    with pytest.raises(RuntimeError, match='declares no null value'):
        resolve_schema(tdir, 'sky')


def test_missing_format_is_an_error(tmp_path: Path) -> None:
    """A geometry column with no FORMAT has no defined width, so it fails."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '    FORMAT                      = "F10.6"\n', '')
    with pytest.raises(RuntimeError, match='declares no FORMAT'):
        resolve_schema(tdir, 'sky')


def test_empty_valid_range_is_an_error(tmp_path: Path) -> None:
    """VALID_MINIMUM == VALID_MAXIMUM would null every value, so it is rejected."""
    host = _host_dir(tmp_path)
    # Both halves, or the halves derive different conversions and that check
    # fires first.
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '    VALID_MAXIMUM               = 360.',
                            '    VALID_MAXIMUM               = 0.', count=2)
    with pytest.raises(RuntimeError, match='empty valid range'):
        resolve_schema(tdir, 'sky')


def test_halves_deriving_different_conversions_is_an_error(tmp_path: Path) -> None:
    """A pair whose halves disagree on unit or range is rejected.

    The conversion is derived per column object, so halves that disagree would
    tabulate one slot in degrees and the other in radians.
    """
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '    VALID_MAXIMUM               = 360.',
                            '    VALID_MAXIMUM               = 180.', count=1)
    with pytest.raises(RuntimeError, match='derive different conversions'):
        resolve_schema(tdir, 'sky')


def test_unrecognized_unit_is_an_error(tmp_path: Path) -> None:
    """An unrecognized UNIT is rejected rather than guessed at.

    The unit decides the conversion, so a misspelling that fell through to "no
    conversion" would silently tabulate radians in a column labelled degrees.
    """
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '    UNIT                        = "deg"',
                            '    UNIT                        = "dgrees"', count=1)
    with pytest.raises(RuntimeError, match='not a recognized PDS3 unit'):
        resolve_schema(tdir, 'sky')


def test_a_host_may_omit_columns(tmp_path: Path) -> None:
    """Dropping a column pair from a template drops it from the table.

    This is how a host trims its column set: a catalog entry the template never
    names is simply unused, not an error.
    """
    host = _host_dir(tmp_path)
    source = Path(metadata_tools.__file__).parent / 'templates' / 'sky_summary_columns.lbl'
    text = source.read_text(encoding='utf-8')
    # Drop the whole right-ascension pair, i.e. everything before the first
    # declination COLUMN object.
    cut = text.index('  OBJECT                        = COLUMN',
                     text.index('"MAXIMUM_RIGHT_ASCENSION"'))
    (host / 'templates' / 'sky_summary_columns.lbl').write_text(text[cut:], encoding='utf-8')

    schema = resolve_schema(FCPath(host / 'templates'), 'sky')
    names = [stub.name for column in schema.columns for stub in column.stubs]
    assert names == ['MINIMUM_DECLINATION', 'MAXIMUM_DECLINATION']


def test_catalog_covers_every_shipped_template_name() -> None:
    """Every NAME in every shipped template resolves to a catalog entry."""
    for qualifier in sorted(SHIPPED):
        mapping = name_map(qualifier)
        for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
            for stub in column.stubs:
                assert stub.name in mapping
