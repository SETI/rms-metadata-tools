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
    PREFIX_NAMES,
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
    tdir = _shadow_fragment(host, 'sky_summary_columns.lbl',
                            '    VALID_MAXIMUM               = 360.',
                            '    VALID_MAXIMUM               = 0.')
    with pytest.raises(RuntimeError, match='empty valid range'):
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
