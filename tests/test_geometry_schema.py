################################################################################
# tests/test_geometry_schema.py: resolve_schema against real and synthetic
# templates.
################################################################################
"""Tests for the template pull: label template -> resolved column schema.

These are the drift guard. All end-to-end geometry verification is archive
gated and off by default, so if a template stops resolving -- or resolves to
the wrong shape -- this is where it must surface.

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
import metadata_tools.defs as defs
import metadata_tools.util as util
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

# The shipped GO_0xxx templates: (data columns, computation groups).
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
    values, groups = SHIPPED[qualifier]
    schema = resolve_schema(TEMPLATE_DIR, qualifier)

    assert len(schema.prefix_stubs) == len(PREFIX_NAMES[qualifier])
    assert len(schema.columns) == groups
    assert sum(len(column.stubs) for column in schema.columns) == values


@pytest.mark.parametrize('qualifier', sorted(SHIPPED))
def test_every_data_column_declares_a_null(qualifier: str) -> None:
    """A geometry column with no null would write one the label never mentions."""
    for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
        for stub in column.stubs:
            assert stub.null_value is not None, stub.name


@pytest.mark.parametrize('qualifier', sorted(SHIPPED))
def test_every_column_states_its_computation(qualifier: str) -> None:
    """Each resolved column carries a non-empty backplane key and a 3-part mask."""
    for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
        assert isinstance(column.key, tuple), column.stubs[0].name
        assert column.key, column.stubs[0].name
        assert len(column.mask) == 3


@pytest.mark.parametrize('qualifier', ['body', 'ring'])
def test_body_and_ring_keys_carry_the_placeholder(qualifier: str) -> None:
    """Every body and ring key is written against the BODYX token.

    The token is bound per body at add time; a typo like 'bodx' would
    otherwise surface only as an oops evaluation failure in an archive run.
    """
    for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
        assert defs.BODYX in str(column.key), column.stubs[0].name


@pytest.mark.parametrize('qualifier', ['sky', 'sun'])
def test_sky_and_sun_keys_are_already_bound(qualifier: str) -> None:
    """Sky and sun columns have no per-body variation, so no placeholder."""
    for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
        assert defs.BODYX not in str(column.key), column.stubs[0].name


def test_ring_diameter_key_holds_a_dict_reference() -> None:
    """The ring diameter key defers a RING_SYSTEM_RADII lookup to substitution."""
    columns = {c.stubs[0].name: c for c in resolve_schema(TEMPLATE_DIR, 'ring').columns}
    assert 'RING_SYSTEM_RADII' in str(columns['RING_DIAMETER_IN_PIXELS'].key)


def test_only_the_centre_coordinates_are_linked() -> None:
    """The null link groups the centre coordinates and nothing else."""
    linked = {stub.name
              for qualifier in sorted(SHIPPED)
              for column in resolve_schema(TEMPLATE_DIR, qualifier).columns
              for stub in column.stubs
              if column.link_id}
    assert linked == {'CENTER_X_COORDINATE', 'CENTER_Y_COORDINATE',
                      'RING_CENTER_X_COORDINATE', 'RING_CENTER_Y_COORDINATE'}


def test_linked_columns_share_a_group_within_a_qualifier() -> None:
    """Columns that go null together carry the same link function and id."""
    for qualifier in sorted(SHIPPED):
        groups = {(column.link_fn, column.link_id)
                  for column in resolve_schema(TEMPLATE_DIR, qualifier).columns
                  if column.link_id}
        assert len(groups) <= 1, f'{qualifier} has several link groups: {groups}'


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
    assert sunward.key[0] == prograde.key[0]


def test_intercept_time_null_is_unquoted() -> None:
    """Pds3Table strips the quotes from NULL_CONSTANT = "NA"."""
    columns = {c.stubs[0].name: c for c in resolve_schema(TEMPLATE_DIR, 'body').columns}
    stub = columns['MINIMUM_SURFACE_INTERCEPT_TIME'].stubs[0]
    assert stub.null_value == 'NA'
    # A quoted 23-character payload occupies a 25-character field.
    assert (stub.width, stub.print_format) == (25, '%25s')
    # Its overflow is the same A23, i.e. the string form of the field itself.
    assert stub.overflow_format == '%25s'


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
    """The sun table is not wired in, but its template must keep resolving."""
    schema = resolve_schema(TEMPLATE_DIR, 'sun')
    assert len(schema.columns) == SHIPPED['sun'][1]


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
# Overflow formats
#===============================================================================
@pytest.mark.parametrize('qualifier', sorted(SHIPPED))
def test_overflow_formats_fill_their_field(qualifier: str) -> None:
    """Every shipped stub's overflow format writes exactly its field width.

    formatted_column substitutes the overflow format and truncates an over-wide
    result, but never pads. A narrow one writes a short field and shifts every
    later column on the row.
    """
    for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
        for stub in column.stubs:
            if stub.overflow_format is not None:
                assert len(stub.overflow_format % 1.0) == stub.width, stub.name


@pytest.mark.parametrize('qualifier', sorted(SHIPPED))
def test_overflow_is_declared_per_stub(qualifier: str) -> None:
    """Within a group, every stub agrees on whether (and how) it overflows."""
    for column in resolve_schema(TEMPLATE_DIR, qualifier).columns:
        formats = {stub.overflow_format for stub in column.stubs}
        assert len(formats) == 1, column.stubs[0].name


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


def test_write_path_lowers_and_strips_the_grammar() -> None:
    """The lowered fragment carries no trace of the authoring grammar.

    This is the forgotten-merge tripwire: neither block kind nor any spec
    keyword is PDS3, so none of it may reach a shipped label.
    """
    from metadata_tools.column_grammar import merge_column_definitions
    from metadata_tools.label_support import _strip_private_keywords

    fragment = (Path(metadata_tools.__file__).parent / 'templates' /
                'ring_summary_columns.lbl').read_text()
    # The header $NOTE documents the grammar in prose; the shipped-label check
    # concerns keyword lines and OBJECT kinds, which prose never forms.
    lowered = _strip_private_keywords(None, merge_column_definitions(None, fragment))
    for keyword in label_schema.PRIVATE_KEYWORDS:
        assert not re.search(r'(?m)^ *' + keyword + r' *=', lowered), keyword
    assert not re.search(r'(?m)^ *(END_)?OBJECT *= *COLUMN_(DEFINITION|STUB)', lowered)

    # Every shipped column emerges complete: one FORMAT and one null each.
    def lines(text: str, keyword: str) -> int:
        return len(re.findall(r'(?m)^ *' + keyword + r' *=', text))

    assert lines(lowered, 'FORMAT') == 81
    assert lines(lowered, 'NULL_CONSTANT') == 81
    assert len(re.findall(r'(?m)^ *OBJECT *= *COLUMN *$', lowered)) == 81


def test_strip_alternation_matches_the_reader() -> None:
    """label_support strips exactly the keyword set label_schema reads."""
    from metadata_tools.label_support import _PRIVATE_KEYWORD_RE

    for keyword in label_schema.PRIVATE_KEYWORDS:
        assert _PRIVATE_KEYWORD_RE.match(f'    {keyword} = x\n'), keyword


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
    """The shadowing the failure-mode tests rely on actually takes effect.

    Renaming a column is legal -- NAMEs no longer join to anything -- so the
    proof is the renamed stub appearing in the resolved schema.
    """
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '"MINIMUM_DECLINATION"', '"MINIMUM_RENAMED"')
    schema = resolve_schema(tdir, 'sky')
    names = [stub.name for column in schema.columns for stub in column.stubs]
    assert 'MINIMUM_RENAMED' in names


def test_missing_backplane_key_is_an_error(tmp_path: Path) -> None:
    """A definition without a BACKPLANE_KEY defines nothing computable."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            "    BACKPLANE_KEY               = ('right_ascension', ())\n",
                            '')
    with pytest.raises(RuntimeError, match='declares no BACKPLANE_KEY'):
        resolve_schema(tdir, 'sky')


def test_spec_keyword_on_a_stub_is_an_error(tmp_path: Path) -> None:
    """A stub carrying its own BACKPLANE_KEY is rejected.

    The computation belongs to the definition; a spec keyword on a stub
    usually means a definition and its stubs have drifted apart.
    """
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(
        host, 'sky_summary_columns.lbl',
        '    NAME                        = "MAXIMUM_RIGHT_ASCENSION"\n',
        '    NAME                        = "MAXIMUM_RIGHT_ASCENSION"\n'
        "    BACKPLANE_KEY               = ('right_ascension', ())\n")
    with pytest.raises(RuntimeError, match='belongs on its COLUMN_DEFINITION'):
        resolve_schema(tdir, 'sky')


def test_stub_without_a_definition_is_an_error(tmp_path: Path) -> None:
    """A stub with no preceding definition cannot be computed."""
    host = _host_dir(tmp_path)
    source = Path(metadata_tools.__file__).parent / 'templates' / 'sky_summary_columns.lbl'
    text = source.read_text(encoding='utf-8')
    # Delete the right-ascension definition block, stranding its stubs.
    start = text.index('  OBJECT                        = COLUMN_DEFINITION')
    end = text.index('END_OBJECT                    = COLUMN_DEFINITION', start)
    end = text.index('\n', end) + 1
    (host / 'templates' / 'sky_summary_columns.lbl').write_text(
        text[:start] + text[end:], encoding='utf-8')
    with pytest.raises(RuntimeError, match='no preceding COLUMN_DEFINITION'):
        resolve_schema(FCPath(host / 'templates'), 'sky')


def test_a_keyed_plain_column_is_a_single_column(tmp_path: Path) -> None:
    """A plain COLUMN carrying its own spec keywords is a single-valued column.

    This is the form of the twelve single-valued columns: one self-contained
    COLUMN, no definition and no stub.
    """
    host = _host_dir(tmp_path)
    source = Path(metadata_tools.__file__).parent / 'templates' / 'sky_summary_columns.lbl'
    extra = """
  OBJECT                        = COLUMN
    NAME                        = "STANDALONE"
    FORMAT                      = "F10.3"
    NULL_CONSTANT               = -999.
    BACKPLANE_KEY               = ('standalone', ())
    DESCRIPTION                 = "A single-valued column."
  END_OBJECT                    = COLUMN
"""
    (host / 'templates' / 'sky_summary_columns.lbl').write_text(
        source.read_text(encoding='utf-8') + extra, encoding='utf-8')

    schema = resolve_schema(FCPath(host / 'templates'), 'sky')
    last = schema.columns[-1]
    assert last.key == ('standalone', ())
    assert [stub.name for stub in last.stubs] == ['STANDALONE']


def test_a_stubless_definition_is_an_error(tmp_path: Path) -> None:
    """A definition with no stubs shares nothing; write a plain COLUMN."""
    host = _host_dir(tmp_path)
    source = Path(metadata_tools.__file__).parent / 'templates' / 'sky_summary_columns.lbl'
    extra = """
  OBJECT                        = COLUMN_DEFINITION
    NAME                        = "DANGLING"
    FORMAT                      = "F10.3"
    NULL_CONSTANT               = -999.
    BACKPLANE_KEY               = ('dangling', ())
  END_OBJECT                    = COLUMN_DEFINITION
"""
    (host / 'templates' / 'sky_summary_columns.lbl').write_text(
        source.read_text(encoding='utf-8') + extra, encoding='utf-8')
    with pytest.raises(RuntimeError, match='a single-valued column is a plain COLUMN'):
        resolve_schema(FCPath(host / 'templates'), 'sky')


def test_three_stubs_is_an_error(tmp_path: Path) -> None:
    """No computation produces more than two values, so a third stub fails."""
    host = _host_dir(tmp_path)
    stub = """
  OBJECT                        = COLUMN_STUB
    NAME                        = "MEDIAN_DECLINATION"
    DESCRIPTION                 = "A third value nothing computes."
  END_OBJECT                    = COLUMN_STUB
"""
    source = Path(metadata_tools.__file__).parent / 'templates' / 'sky_summary_columns.lbl'
    (host / 'templates' / 'sky_summary_columns.lbl').write_text(
        source.read_text(encoding='utf-8') + stub, encoding='utf-8')
    with pytest.raises(RuntimeError, match='no computation produces more than two'):
        resolve_schema(FCPath(host / 'templates'), 'sky')


def test_a_keyless_column_in_the_data_region_is_an_error(tmp_path: Path) -> None:
    """A COLUMN among the groups with no BACKPLANE_KEY cannot be computed."""
    host = _host_dir(tmp_path)
    column = """
  OBJECT                        = COLUMN
    NAME                        = "LOOSE_COLUMN"
    FORMAT                      = "F10.3"
    NULL_CONSTANT               = -999.
    DESCRIPTION                 = "A column with no computation."
  END_OBJECT                    = COLUMN
"""
    source = Path(metadata_tools.__file__).parent / 'templates' / 'sky_summary_columns.lbl'
    (host / 'templates' / 'sky_summary_columns.lbl').write_text(
        source.read_text(encoding='utf-8') + column, encoding='utf-8')
    with pytest.raises(RuntimeError, match='carries no BACKPLANE_KEY'):
        resolve_schema(FCPath(host / 'templates'), 'sky')


def test_mismatched_object_kinds_are_an_error(tmp_path: Path) -> None:
    """An OBJECT whose END_OBJECT names a different kind fails loudly.

    The tokenizer would otherwise skip the malformed block silently, and a
    skipped column is exactly the misalignment this module exists to prevent.
    """
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(
        host, 'sky_summary_columns.lbl',
        '  OBJECT                        = COLUMN_STUB\n'
        '    NAME                        = "MAXIMUM_DECLINATION"\n',
        '  OBJECT                        = COLUMN\n'
        '    NAME                        = "MAXIMUM_DECLINATION"\n')
    with pytest.raises(RuntimeError, match='malformed COLUMN object'):
        resolve_schema(tdir, 'sky')


def test_duplicate_private_keyword_is_an_error(tmp_path: Path) -> None:
    """One COLUMN declaring a private keyword twice is ambiguous, so it fails."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(
        host, 'sky_summary_columns.lbl',
        "    BACKPLANE_KEY               = ('right_ascension', ())\n",
        "    BACKPLANE_KEY               = ('right_ascension', ())\n"
        "    BACKPLANE_KEY               = ('declination', ())\n")
    with pytest.raises(RuntimeError, match='declares BACKPLANE_KEY 2 times'):
        resolve_schema(tdir, 'sky')


def test_unparseable_literal_is_an_error(tmp_path: Path) -> None:
    """A BACKPLANE_KEY that is not a Python literal names itself in the error."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            "BACKPLANE_KEY               = ('right_ascension', ())",
                            "BACKPLANE_KEY               = ('right_ascension', (")
    with pytest.raises(RuntimeError, match='unparseable BACKPLANE_KEY'):
        resolve_schema(tdir, 'sky')


def test_non_tuple_key_is_an_error(tmp_path: Path) -> None:
    """A BACKPLANE_KEY that parses but is not a tuple is rejected."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            "BACKPLANE_KEY               = ('right_ascension', ())",
                            "BACKPLANE_KEY               = 'right_ascension'")
    with pytest.raises(RuntimeError, match='must be a tuple'):
        resolve_schema(tdir, 'sky')


def test_short_key_is_an_error(tmp_path: Path) -> None:
    """A BACKPLANE_KEY without a target slot is rejected at parse time.

    prep_row reads the key's second element as the mask target, so a
    one-element key would raise IndexError per observation instead.
    """
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            "BACKPLANE_KEY               = ('right_ascension', ())",
                            "BACKPLANE_KEY               = ('right_ascension',)")
    with pytest.raises(RuntimeError, match='needs at least two elements'):
        resolve_schema(tdir, 'sky')


def test_half_specified_link_is_an_error(tmp_path: Path) -> None:
    """LINK_FN and LINK_ID must be given together or not at all."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(
        host, 'sky_summary_columns.lbl',
        "    BACKPLANE_KEY               = ('right_ascension', ())\n",
        "    BACKPLANE_KEY               = ('right_ascension', ())\n"
        '    LINK_ID                     = "LINK-X"\n')
    with pytest.raises(RuntimeError, match='must be given together'):
        resolve_schema(tdir, 'sky')


def test_unknown_link_function_is_an_error(tmp_path: Path) -> None:
    """A LINK_FN postprocess cannot dispatch fails at parse time, not add time."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(
        host, 'sky_summary_columns.lbl',
        "    BACKPLANE_KEY               = ('right_ascension', ())\n",
        "    BACKPLANE_KEY               = ('right_ascension', ())\n"
        '    LINK_FN                     = "bogus"\n'
        '    LINK_ID                     = "LINK-X"\n')
    with pytest.raises(RuntimeError, match='not a known link function'):
        resolve_schema(tdir, 'sky')


def test_private_keyword_on_prefix_column_is_an_error(tmp_path: Path) -> None:
    """Prefix columns are not computed, so a spec keyword there is an error.

    A BACKPLANE_KEY on a leading column would instead end the prefix run and
    fail the prefix-name check; any other spec keyword hits this pointed
    error.
    """
    host = _host_dir(tmp_path)
    path = host / 'templates' / 'GO_0xxx_sky_summary.lbl'
    text = path.read_text(encoding='utf-8')
    needle = '    NAME                        = "VOLUME_ID"\n'
    assert needle in text
    path.write_text(text.replace(
        needle, needle + "    MASK                        = ('P', '', '')\n", 1),
        encoding='utf-8')
    with pytest.raises(RuntimeError, match='prefix columns are not computed'):
        resolve_schema(FCPath(host / 'templates'), 'sky')


def test_narrow_overflow_format_is_an_error(tmp_path: Path) -> None:
    """An overflow format narrower than the field is rejected at parse time."""
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '    OVERFLOW_FORMAT             = "F10.5"\n',
                            '    OVERFLOW_FORMAT             = "F8.3"\n')
    with pytest.raises(RuntimeError, match='must fill the field exactly'):
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


def test_stubs_deriving_different_conversions_is_an_error(tmp_path: Path) -> None:
    """A stub whose override changes the derived conversion is rejected.

    The conversion is derived per stub, so an override that disagrees would
    tabulate one slot as cyclic coverage and the other as a plain min/max.
    """
    host = _host_dir(tmp_path)
    tdir = _shadow_fragment(
        host, 'sky_summary_columns.lbl',
        '    NAME                        = "MAXIMUM_RIGHT_ASCENSION"\n',
        '    NAME                        = "MAXIMUM_RIGHT_ASCENSION"\n'
        '    VALID_MAXIMUM               = 180.\n')
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

    This is how a host trims its column set: the computation travels with the
    COLUMN objects, so removing them removes the column and nothing else.
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


def test_a_host_may_rename_and_add_columns(tmp_path: Path) -> None:
    """A host template can define a brand-new column with no engine edit.

    The computation spec travels with the COLUMN object, so a host-local
    column needs nothing beyond its template text.
    """
    host = _host_dir(tmp_path)
    source = Path(metadata_tools.__file__).parent / 'templates' / 'sky_summary_columns.lbl'
    extra = """
  OBJECT                        = COLUMN_DEFINITION
    NAME                        = "SOMETHING_NEW"
    FORMAT                      = "F10.3"
    NULL_CONSTANT               = -999.
    BACKPLANE_KEY               = ('something_new', ())
  END_OBJECT                    = COLUMN_DEFINITION

  OBJECT                        = COLUMN_STUB
    NAME                        = "MEAN_SOMETHING_NEW"
    DESCRIPTION                 = "A host-local column."
  END_OBJECT                    = COLUMN_STUB
"""
    (host / 'templates' / 'sky_summary_columns.lbl').write_text(
        source.read_text(encoding='utf-8') + extra, encoding='utf-8')

    schema = resolve_schema(FCPath(host / 'templates'), 'sky')
    last = schema.columns[-1]
    assert last.key == ('something_new', ())
    assert [stub.name for stub in last.stubs] == ['MEAN_SOMETHING_NEW']
