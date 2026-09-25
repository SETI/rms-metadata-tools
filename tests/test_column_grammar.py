################################################################################
# tests/test_column_grammar.py: the definition/stub grammar and its lowering.
################################################################################
"""Unit tests for ``column_grammar``: tokenizing and write-path lowering.

The schema reader's use of the grammar is tested against the shipped templates
in ``tests/test_geometry_schema.py``; these tests pin the lowering semantics
the write path depends on, on small synthetic templates.
"""
import pytest

from metadata_tools.column_grammar import (
    expand_format_references,
    keyword_value,
    merge_column_definitions,
    strip_comments,
    tokenize,
)

_GROUP = """\
  OBJECT                        = COLUMN_DEFINITION
    NAME                        = "QUANTITY"
    FORMAT                      = "F10.3"
    UNIT                        = "km"
    NULL_CONSTANT               = -999.
    BACKPLANE_KEY               = ('quantity', 'bodyx')
    MASK                        = ('PM', 'P', '')
  END_OBJECT                    = COLUMN_DEFINITION

  OBJECT                        = COLUMN_STUB
    NAME                        = "MINIMUM_QUANTITY"
    DESCRIPTION                 = "The minimum."
  END_OBJECT                    = COLUMN_STUB

  OBJECT                        = COLUMN_STUB
    NAME                        = "MAXIMUM_QUANTITY"
    UNIT                        = "km/pixel"
    DESCRIPTION                 = "The maximum."
  END_OBJECT                    = COLUMN_STUB
"""


def test_lowering_produces_complete_plain_columns() -> None:
    """Each stub becomes a COLUMN carrying the definition's shippable lines."""
    lowered = merge_column_definitions(None, _GROUP)
    assert 'COLUMN_DEFINITION' not in lowered
    assert 'COLUMN_STUB' not in lowered
    assert 'BACKPLANE_KEY' not in lowered
    assert 'MASK' not in lowered
    assert lowered.count('FORMAT                      = "F10.3"') == 2
    assert lowered.count('NULL_CONSTANT               = -999.') == 2


def test_lowering_places_an_override_at_the_definition_position() -> None:
    """A stub's override replaces the definition's line in place.

    The shipped column's keyword order is the definition's, so an override
    must not drift to the end of the keyword region.
    """
    lowered = merge_column_definitions(None, _GROUP)
    blocks = tokenize(lowered)
    maximum = next(b for b in blocks
                   if '"MAXIMUM_QUANTITY"' in b.body)
    keywords = [line.split('=')[0].strip()
                for line in maximum.body.splitlines()
                if '=' in line and not line.lstrip().startswith('DESCRIPTION')][:4]
    assert keywords == ['NAME', 'FORMAT', 'UNIT', 'NULL_CONSTANT']
    assert keyword_value(maximum.body, 'UNIT') == '"km/pixel"'


def test_lowering_keeps_each_stub_description() -> None:
    """Per-stub descriptions ship verbatim."""
    lowered = merge_column_definitions(None, _GROUP)
    assert '"The minimum."' in lowered
    assert '"The maximum."' in lowered


def test_lowering_falls_back_to_the_definition_description() -> None:
    """A stub without a DESCRIPTION ships the definition's.

    This is the shared-description mechanism for two-valued columns.
    """
    template = _GROUP.replace('    DESCRIPTION                 = "The minimum."\n', '')
    template = template.replace(
        "    MASK                        = ('PM', 'P', '')\n",
        "    MASK                        = ('PM', 'P', '')\n"
        '    DESCRIPTION                 = "Both extremes."\n')
    lowered = merge_column_definitions(None, template)
    minimum = next(b for b in tokenize(lowered) if '"MINIMUM_QUANTITY"' in b.body)
    assert '"Both extremes."' in minimum.body


def test_lowering_composes_definition_and_stub_descriptions() -> None:
    """A stub's DESCRIPTION continues the definition's.

    The definition carries the shared lead-in; the stub's per-value prose
    follows after a blank line, re-flowed to house style, and the closing
    quote comes from the stub's text.
    """
    template = _GROUP.replace(
        "    MASK                        = ('PM', 'P', '')\n",
        "    MASK                        = ('PM', 'P', '')\n"
        '    DESCRIPTION                 = "The quantity, defined."\n')
    lowered = merge_column_definitions(None, template)
    minimum = next(b for b in tokenize(lowered) if '"MINIMUM_QUANTITY"' in b.body)
    assert ('    DESCRIPTION                 = "The quantity, defined.\n'
            '\n'
            '      The minimum."\n') in minimum.body


def test_lowering_keeps_a_directive_paragraph_verbatim() -> None:
    """A $INCLUDE paragraph in a stub description is never re-flowed."""
    template = _GROUP.replace(
        "    MASK                        = ('PM', 'P', '')\n",
        "    MASK                        = ('PM', 'P', '')\n"
        '    DESCRIPTION                 = "The quantity, defined."\n')
    template = template.replace(
        '    DESCRIPTION                 = "The minimum."\n',
        '    DESCRIPTION                 = "The minimum.\n'
        '\n'
        "      $INCLUDE('details.lbl')\n")
    lowered = merge_column_definitions(None, template)
    minimum = next(b for b in tokenize(lowered) if '"MINIMUM_QUANTITY"' in b.body)
    assert "\n\n      $INCLUDE('details.lbl')\n" in minimum.body


def test_lowering_passes_plain_templates_through() -> None:
    """A template with no grammar blocks is returned unchanged."""
    plain = ('  OBJECT                        = COLUMN\n'
             '    NAME                        = "VOLUME_ID"\n'
             '  END_OBJECT                    = COLUMN\n')
    assert merge_column_definitions(None, plain) == plain


def test_lowering_rejects_a_stranded_stub() -> None:
    """A stub with no preceding definition cannot be lowered."""
    stub_only = _GROUP.split('END_OBJECT                    = COLUMN_DEFINITION\n')[1]
    with pytest.raises(ValueError, match='no preceding COLUMN_DEFINITION'):
        merge_column_definitions(None, stub_only)


def test_lowering_rejects_a_stubless_definition() -> None:
    """A definition with no stubs shares nothing; write a plain COLUMN."""
    definition_only = _GROUP.split('\n\n')[0] + '\n'
    with pytest.raises(ValueError, match='a single-valued column is a plain COLUMN'):
        merge_column_definitions(None, definition_only)


def test_lowering_strips_spec_keywords_from_plain_columns() -> None:
    """A self-contained single COLUMN ships minus its spec keyword lines."""
    column = ('  OBJECT                        = COLUMN\n'
              '    NAME                        = "STANDALONE"\n'
              '    FORMAT                      = "F10.3"\n'
              '    OVERFLOW_FORMAT             = "E10.4"\n'
              '    NULL_CONSTANT               = -999.\n'
              "    BACKPLANE_KEY               = ('standalone', ())\n"
              "    MASK                        = ('PM', 'P', '')\n"
              '    DESCRIPTION                 = "A single-valued column."\n'
              '  END_OBJECT                    = COLUMN\n')
    lowered = merge_column_definitions(None, _GROUP + '\n' + column)
    standalone = next(b for b in tokenize(lowered) if '"STANDALONE"' in b.body)
    assert 'BACKPLANE_KEY' not in standalone.body
    assert 'MASK' not in standalone.body
    assert 'OVERFLOW_FORMAT' not in standalone.body
    assert 'FORMAT                      = "F10.3"' in standalone.body
    assert '"A single-valued column."' in standalone.body


def test_tokenize_rejects_a_mismatched_block() -> None:
    """An opener whose END_OBJECT names another kind must not be skipped."""
    broken = _GROUP.replace('  END_OBJECT                    = COLUMN_DEFINITION\n',
                            '  END_OBJECT                    = COLUMN\n', 1)
    with pytest.raises(ValueError, match='malformed COLUMN_DEFINITION'):
        tokenize(broken)


def test_tokenize_rejects_a_body_that_swallowed_a_block() -> None:
    """A mismatched footer is rejected even when a later footer matches.

    Otherwise the blocks between the two footers would silently vanish from
    the tokenization, and with them their columns.
    """
    broken = (_GROUP + '\n' + _GROUP).replace(
        '  END_OBJECT                    = COLUMN_DEFINITION\n',
        '  END_OBJECT                    = COLUMN\n', 1)
    with pytest.raises(ValueError, match='malformed'):
        tokenize(broken)


def test_tokenize_rejects_a_swallowed_block_with_crlf_endings() -> None:
    """The mismatched-footer rejection also fires in a CRLF template."""
    broken = (_GROUP + '\n' + _GROUP).replace(
        '  END_OBJECT                    = COLUMN_DEFINITION\n',
        '  END_OBJECT                    = COLUMN\n', 1)
    with pytest.raises(ValueError, match='malformed'):
        tokenize(broken.replace('\n', '\r\n'))


def test_keyword_value_rejects_a_duplicate() -> None:
    """A keyword declared twice in one block is ambiguous."""
    with pytest.raises(ValueError, match='declares UNIT 2 times'):
        keyword_value('    UNIT = "km"\n    UNIT = "deg"\n', 'UNIT')


#===============================================================================
# The format dictionary
#===============================================================================
_ENTRY = """\
  OBJECT                        = COLUMN_FORMAT
    NAME                        = "DISTANCE_KM"
    FORMAT                      = "F12.3"
    OVERFLOW_FORMAT             = "E12.5"
    UNIT                        = "km"
    NULL_CONSTANT               = -999.
  END_OBJECT                    = COLUMN_FORMAT
"""

_REFERRING_GROUP = """\
  OBJECT                        = COLUMN_DEFINITION
    NAME                        = "QUANTITY"
    COLUMN_FORMAT               = "DISTANCE_KM"
    BACKPLANE_KEY               = ('quantity', 'bodyx')
    DESCRIPTION                 = "The quantity."
  END_OBJECT                    = COLUMN_DEFINITION

  OBJECT                        = COLUMN_STUB
    NAME                        = "MINIMUM_QUANTITY"
  END_OBJECT                    = COLUMN_STUB

  OBJECT                        = COLUMN_STUB
    NAME                        = "MAXIMUM_QUANTITY"
  END_OBJECT                    = COLUMN_STUB
"""


def _expand(text: str) -> str:
    """Expand a synthetic template whose dictionary precedes its columns."""
    return expand_format_references(None, _ENTRY + '\n' + text)


def test_expansion_replaces_a_reference_in_place() -> None:
    """The entry's lines take the reference's place, in the entry's order."""
    definition = tokenize(_expand(_REFERRING_GROUP))[0]
    assert definition.body == (
        '    NAME                        = "QUANTITY"\n'
        '    FORMAT                      = "F12.3"\n'
        '    OVERFLOW_FORMAT             = "E12.5"\n'
        '    UNIT                        = "km"\n'
        '    NULL_CONSTANT               = -999.\n'
        "    BACKPLANE_KEY               = ('quantity', 'bodyx')\n"
        '    DESCRIPTION                 = "The quantity."\n')


def test_expansion_removes_the_dictionary() -> None:
    """No entry survives expansion, and neither does any reference."""
    expanded = _expand(_REFERRING_GROUP)
    assert 'COLUMN_FORMAT' not in expanded
    assert [block.kind for block in tokenize(expanded)] == [
        'COLUMN_DEFINITION', 'COLUMN_STUB', 'COLUMN_STUB']


def test_expansion_keeps_text_around_an_entry() -> None:
    """Only the blank lines before an entry go with it; other text stays."""
    note = '$NOTE\nThe dictionary.\n$END_NOTE\n'
    expanded = expand_format_references(None, note + _ENTRY + '\n' + _REFERRING_GROUP)
    assert expanded.startswith(note + '\n  OBJECT                        = COLUMN_DEFINITION')


def test_a_stated_keyword_beats_the_entry() -> None:
    """A keyword the column states itself is not replaced by the entry's."""
    group = _REFERRING_GROUP.replace(
        '    COLUMN_FORMAT               = "DISTANCE_KM"\n',
        '    COLUMN_FORMAT               = "DISTANCE_KM"\n'
        '    NULL_CONSTANT               = -99999.\n')
    body = tokenize(_expand(group))[0].body
    assert keyword_value(body, 'NULL_CONSTANT') == '-99999.'
    assert keyword_value(body, 'FORMAT') == '"F12.3"'


def test_a_stub_reference_overrides_the_definition() -> None:
    """A stub's expanded lines are its own, so they win in the lowering."""
    entry = _ENTRY.replace('"DISTANCE_KM"', '"PER_PIXEL"').replace(
        '"km"', '"km/pixel"')
    group = _REFERRING_GROUP.replace(
        '    NAME                        = "MAXIMUM_QUANTITY"\n',
        '    NAME                        = "MAXIMUM_QUANTITY"\n'
        '    COLUMN_FORMAT               = "PER_PIXEL"\n')
    lowered = merge_column_definitions(
        None, expand_format_references(None, _ENTRY + '\n' + entry + '\n' + group))
    minimum, maximum = tokenize(lowered)
    assert keyword_value(minimum.body, 'UNIT') == '"km"'
    assert keyword_value(maximum.body, 'UNIT') == '"km/pixel"'


def test_a_plain_column_may_refer_to_an_entry() -> None:
    """A self-contained single-valued column takes an entry like a definition."""
    column = ('  OBJECT                        = COLUMN\n'
              '    NAME                        = "STANDALONE"\n'
              '    COLUMN_FORMAT               = "DISTANCE_KM"\n'
              "    BACKPLANE_KEY               = ('standalone', ())\n"
              '  END_OBJECT                    = COLUMN\n')
    body = tokenize(_expand(column))[0].body
    assert keyword_value(body, 'UNIT') == '"km"'


def test_expansion_reindents_to_the_reference() -> None:
    """Entry lines take the reference's indentation, whatever the entry's."""
    entry = _ENTRY.replace('\n    ', '\n  ')
    group = _REFERRING_GROUP.replace('    COLUMN_FORMAT', '      COLUMN_FORMAT')
    body = tokenize(expand_format_references(None, entry + '\n' + group))[0].body
    assert '\n      FORMAT                      = "F12.3"\n' in body


def test_expansion_passes_plain_templates_through() -> None:
    """Content with neither entries nor references comes back unchanged."""
    assert expand_format_references(None, _GROUP) == _GROUP
    note = 'The COLUMN_FORMAT grammar, described in prose.\n' + _GROUP
    assert expand_format_references(None, note) == note


def test_an_unknown_entry_is_an_error() -> None:
    """A reference naming no entry cannot be expanded."""
    group = _REFERRING_GROUP.replace('"DISTANCE_KM"', '"NO_SUCH_ENTRY"')
    with pytest.raises(ValueError,
                       match=r"'QUANTITY' refers to format entry 'NO_SUCH_ENTRY'"):
        _expand(group)


def test_a_duplicate_entry_is_an_error() -> None:
    """Two entries with one NAME are ambiguous."""
    with pytest.raises(ValueError, match="'DISTANCE_KM' is defined twice"):
        expand_format_references(None, _ENTRY + _ENTRY + _REFERRING_GROUP)


@pytest.mark.parametrize('keyword', ['DESCRIPTION', 'BACKPLANE_KEY', 'COLUMN_FORMAT'])
def test_an_entry_holds_only_format_metadata(keyword: str) -> None:
    """Descriptions, spec keywords, and nested references stay on columns."""
    entry = _ENTRY.replace('    UNIT', f'    {keyword}                 = "x"\n    UNIT')
    with pytest.raises(ValueError, match="format entry 'DISTANCE_KM'"):
        expand_format_references(None, entry + _REFERRING_GROUP)


def test_an_entry_repeating_a_keyword_is_an_error() -> None:
    """An entry stating one keyword twice is ambiguous."""
    entry = _ENTRY.replace('    UNIT', '    FORMAT                      = "F10.3"\n    UNIT')
    with pytest.raises(ValueError, match='declares FORMAT twice'):
        expand_format_references(None, entry + _REFERRING_GROUP)


def test_an_entry_without_a_name_is_an_error() -> None:
    """An entry is found by its NAME, so it must have one."""
    entry = _ENTRY.replace('    NAME                        = "DISTANCE_KM"\n', '')
    with pytest.raises(ValueError, match='exactly one NAME'):
        expand_format_references(None, entry)


def test_an_empty_entry_is_an_error() -> None:
    """An entry with nothing but a NAME shares nothing."""
    entry = ('  OBJECT                        = COLUMN_FORMAT\n'
             '    NAME                        = "EMPTY"\n'
             '  END_OBJECT                    = COLUMN_FORMAT\n')
    with pytest.raises(ValueError, match="'EMPTY' declares no keywords"):
        expand_format_references(None, entry)


def test_a_repeated_reference_is_an_error() -> None:
    """One column refers to at most one entry."""
    group = _REFERRING_GROUP.replace(
        '    COLUMN_FORMAT               = "DISTANCE_KM"\n',
        '    COLUMN_FORMAT               = "DISTANCE_KM"\n' * 2)
    with pytest.raises(ValueError, match="'QUANTITY' declares COLUMN_FORMAT more than once"):
        _expand(group)


def test_a_reference_after_the_description_is_an_error() -> None:
    """A reference belongs with the keywords, not after the prose."""
    group = _REFERRING_GROUP.replace(
        '    COLUMN_FORMAT               = "DISTANCE_KM"\n', '').replace(
        '    DESCRIPTION                 = "The quantity."\n',
        '    DESCRIPTION                 = "The quantity."\n'
        '    COLUMN_FORMAT               = "DISTANCE_KM"\n')
    with pytest.raises(ValueError, match="'QUANTITY' places COLUMN_FORMAT after"):
        _expand(group)


def test_unexpanded_entries_are_rejected_downstream() -> None:
    """Forgetting the expansion fails loudly instead of losing the format."""
    with pytest.raises(ValueError, match='COLUMN_FORMAT entry was never expanded'):
        merge_column_definitions(None, _ENTRY)
    with pytest.raises(ValueError, match='COLUMN_FORMAT reference was never expanded'):
        merge_column_definitions(None, _REFERRING_GROUP)


#===============================================================================
# Comment lines
#===============================================================================
def test_strip_comments_removes_every_comment_line() -> None:
    """A line whose first non-blank character is '#' goes, at any indent."""
    divider = '  #' + '=' * 75 + '\n'
    content = (divider + _GROUP + '\n    # A note.\n\t#tabbed\n#\n' + _GROUP
               + '# Last line, unterminated.')
    assert strip_comments(None, content) == _GROUP + '\n' + _GROUP


def test_strip_comments_keeps_a_later_hash() -> None:
    """A '#' after other text on its line is ordinary text."""
    content = '    NAME = "COLUMN_#1"\n    FORMAT = "A8"  # trailing\n'
    assert strip_comments(None, content) == content


def test_strip_comments_applies_inside_a_description() -> None:
    """The rule is by line, so it applies inside quoted prose too."""
    content = '    DESCRIPTION = "First line\n      # of pixels\n      last."\n'
    assert strip_comments(None, content) == (
        '    DESCRIPTION = "First line\n      last."\n')


def test_strip_comments_handles_crlf() -> None:
    """A CRLF comment line goes with its terminator."""
    assert strip_comments(None, '  #=====\r\nKEEP = 1\r\n') == 'KEEP = 1\r\n'


def test_comments_inside_a_block_are_harmless_once_stripped() -> None:
    """A comment among a column's keywords would end the keyword region,
    which is why every read path strips comments first."""
    commented = _REFERRING_GROUP.replace(
        '    NAME                        = "QUANTITY"\n',
        '    NAME                        = "QUANTITY"\n    # Shared format.\n')
    assert (expand_format_references(None, _ENTRY + strip_comments(None, commented))
            == expand_format_references(None, _ENTRY + _REFERRING_GROUP))
