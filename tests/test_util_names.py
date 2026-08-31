################################################################################
# tests/test_util_names.py: path/name arithmetic helpers in util.py.
################################################################################
"""Tests for the path and name arithmetic helpers in util.py."""
import types

import pytest
from filecache import FCPath

import metadata_tools.util as util


#===============================================================================
# select_dir
#===============================================================================
def test_select_dir_appends_collection_and_volume() -> None:
    """The collection and volume are appended under the metadata tree."""
    tree = FCPath('/holdings/metadata')
    assert util.select_dir(tree, 'GO_0xxx', 'GO_0001').as_posix() == \
        '/holdings/metadata/GO_0xxx/GO_0001'


def test_select_dir_skips_collection_when_already_tail() -> None:
    """A tree already ending in the collection gains only the volume."""
    tree = FCPath('/holdings/metadata/GO_0xxx')
    assert util.select_dir(tree, 'GO_0xxx', 'GO_0001').as_posix() == \
        '/holdings/metadata/GO_0xxx/GO_0001'


#===============================================================================
# get_index_name
#===============================================================================
def test_get_index_name_with_type() -> None:
    """The index name is <volume>_<type>_index."""
    name = util.get_index_name(FCPath('/x/GO_0001'), 'GO_0001', 'supplemental')
    assert name == 'GO_0001_supplemental_index'


def test_get_index_name_without_type() -> None:
    """index_type=None takes the no-suffix branch and yields <volume>_index.

    index_type is annotated str, but None is accepted at runtime; this test
    deliberately exercises that path.
    """
    name = util.get_index_name(FCPath('/x/GO_0001'), 'GO_0001', None)  # type: ignore[arg-type]
    assert name == 'GO_0001_index'


#===============================================================================
# get_template_name
#===============================================================================
def test_get_template_name_substitutes_collection() -> None:
    """The volume ID in the template filename is replaced by the collection."""
    name = util.get_template_name('GO_0001_supplemental_index.lbl', 'GO_0001',
                                  FCPath('/code/GO_0xxx'))
    assert name == 'GO_0xxx_supplemental_index'


#===============================================================================
# parse_template_name
#===============================================================================
def test_parse_template_name_splits_host_and_type() -> None:
    """The name splits into host, index type, and the host templates directory."""
    host, index_type, template_dir = util.parse_template_name('GO_0xxx_supplemental_index')
    assert host == 'GO_0xxx'
    assert index_type == 'supplemental'
    assert template_dir.name == 'templates'


def test_parse_template_name_preserves_host_underscores() -> None:
    """Embedded host underscores survive; only the final segment is the type."""
    host, index_type, _ = util.parse_template_name('HST_WFC3_supplemental_index')
    assert host == 'HST_WFC3'
    assert index_type == 'supplemental'


#===============================================================================
# splitpath / get_volume_subdir
#===============================================================================
def test_splitpath_splits_around_string() -> None:
    """The path splits into the parts before and after the matched component."""
    before, after = util.splitpath(FCPath('/a/b/GO_0001/data/img.lbl'), 'GO_0001')
    assert before.as_posix() == '/a/b'
    assert after.as_posix() == 'data/img.lbl'


def test_splitpath_raises_when_string_not_in_path() -> None:
    """A component absent from the path raises ValueError."""
    with pytest.raises(ValueError, match='not in tuple'):
        util.splitpath(FCPath('/a/b/c.lbl'), 'GO_MISSING')


def test_get_volume_subdir_returns_relative_tail() -> None:
    """The subpath below the volume directory is returned."""
    sub = util.get_volume_subdir(FCPath('/a/GO_0001/data/img.lbl'), 'GO_0001')
    assert sub.as_posix() == 'data/img.lbl'


#===============================================================================
# get_volume_glob
#===============================================================================
def test_get_volume_glob_expands_x_digits() -> None:
    """Trailing 'x' digits expand to [0-9] character classes."""
    assert util.get_volume_glob('GO_0xxx') == 'GO_0[0-9][0-9][0-9]'


def test_get_volume_glob_only_last_segment() -> None:
    """Only the last underscore-separated segment is expanded."""
    assert util.get_volume_glob('COISS_2xxx') == 'COISS_2[0-9][0-9][0-9]'


#===============================================================================
# get_observation_id
#===============================================================================
def test_get_observation_id_reads_subfields() -> None:
    """The observation ID is read from the observation's subfields dict."""
    obs = types.SimpleNamespace(subfields={'dict': {'OBSERVATION_ID': 'C0123'}})
    assert util.get_observation_id(obs) == 'C0123'
