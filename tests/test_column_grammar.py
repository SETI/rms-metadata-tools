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
    keyword_value,
    merge_column_definitions,
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


def test_keyword_value_rejects_a_duplicate() -> None:
    """A keyword declared twice in one block is ambiguous."""
    with pytest.raises(ValueError, match='declares UNIT 2 times'):
        keyword_value('    UNIT = "km"\n    UNIT = "deg"\n', 'UNIT')
