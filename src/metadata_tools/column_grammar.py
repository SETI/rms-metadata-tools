################################################################################
# column_grammar.py - The definition/stub column grammar of geometry templates.
################################################################################
"""The definition/stub grammar shared by the template read and write paths.

A geometry summary template declares each computed column as a *group*: one
``OBJECT = COLUMN_DEFINITION`` block carrying the computation spec and the
label metadata shared by the group's values, followed by one ``OBJECT =
COLUMN_STUB`` block per value, each carrying its NAME, its DESCRIPTION, and
any keyword it overrides. Neither block type is PDS3: the write path lowers
every group to plain ``COLUMN`` objects (see :func:`merge_column_definitions`)
before a label is generated, and the schema reader
(:mod:`metadata_tools.geometry_support.label_schema`) parses the grammar
directly.

This module is deliberately light -- regular expressions and text
manipulation only -- so :mod:`metadata_tools.label_support` can import it
without touching the geometry engine.
"""
import re
from dataclasses import dataclass

# The private keywords carrying the computation spec, allowed only inside
# COLUMN_DEFINITION blocks (OVERFLOW_FORMAT may also appear on a stub as an
# override). label_support strips exactly this set from generated labels;
# tests pin the two against each other.
PRIVATE_KEYWORDS = ('BACKPLANE_KEY', 'MASK', 'OVERFLOW_FORMAT', 'LINK_FN',
                    'LINK_ID')

# Keywords that never reach a merged COLUMN: the private set, the retired
# VALUES keyword (group size is now the stub count), and NAME, which every
# stub states for itself.
_NOT_MERGED = frozenset(PRIVATE_KEYWORDS) | {'VALUES', 'NAME'}

# One OBJECT block of any of the three column-grammar kinds. The alternation
# tries the longer names first, and the END_OBJECT backreference guarantees
# the opening and closing kinds agree.
_BLOCK_RE = re.compile(
    r'(?<![ \w])( *OBJECT *= *(COLUMN_DEFINITION|COLUMN_STUB|COLUMN) *\r?\n)'
    r'(.*?\r?\n)'
    r'( *END_OBJECT *= *\2 *\r?\n)', re.DOTALL)

# A stray opener that _BLOCK_RE did not consume (e.g. mismatched END_OBJECT).
_STRAY_OBJECT_RE = re.compile(
    r'(?m)^ *OBJECT *= *(COLUMN_DEFINITION|COLUMN_STUB|COLUMN) *$')

# One "keyword = value" line, including its terminator. Matched with
# .match(body, pos) where pos is always a line start, so no ^ anchor (which
# would assert the start of the whole string, not of the line at pos).
_KEYWORD_LINE_RE = re.compile(r' *([A-Z][A-Z0-9_]*) *=[^\r\n]*\r?\n')


#===============================================================================
@dataclass(frozen=True)
class Block:
    """One tokenized OBJECT block of the column grammar.

    Attributes:
        kind: ``'COLUMN'``, ``'COLUMN_DEFINITION'``, or ``'COLUMN_STUB'``.
        header: The OBJECT line, terminator included.
        body: The text between the OBJECT and END_OBJECT lines.
        footer: The END_OBJECT line, terminator included.
        start: Offset of the block in the tokenized text.
        end: Offset just past the block.
    """

    kind: str
    header: str
    body: str
    footer: str
    start: int
    end: int


#===============================================================================
def tokenize(content: str) -> list[Block]:
    """Split template content into its column-grammar blocks, in order.

    Parameters:
        content: The template text, includes expanded.

    Returns:
        The blocks, in template order.

    Raises:
        ValueError: If an OBJECT opener of a column kind is not part of a
            well-formed block -- which otherwise would be silently skipped.
    """
    blocks = []
    pos = 0
    for match in _BLOCK_RE.finditer(content):
        _check_no_stray_object(content[pos:match.start()])
        blocks.append(Block(kind=match.group(2), header=match.group(1),
                            body=match.group(3), footer=match.group(4),
                            start=match.start(), end=match.end()))
        pos = match.end()
    _check_no_stray_object(content[pos:])
    return blocks


def _check_no_stray_object(text: str) -> None:
    """Reject an OBJECT opener outside any tokenized block.

    Parameters:
        text: Text between (or around) tokenized blocks.

    Raises:
        ValueError: If a stray opener is found.
    """
    stray = _STRAY_OBJECT_RE.search(text)
    if stray:
        raise ValueError(
            f'malformed {stray.group(1)} object (its END_OBJECT is missing or '
            f'names a different kind)')


#===============================================================================
def keyword_value(body: str, keyword: str) -> str | None:
    """Return the raw right-hand side of one keyword in a block body, or None.

    The line-start anchor keeps uppercase words inside a DESCRIPTION from
    matching; the write-time strip in ``label_support`` anchors the same way,
    so the read and strip can never disagree about what is a keyword line.

    Parameters:
        body: The block body.
        keyword: The keyword to read.

    Returns:
        The right-hand side, trailing whitespace stripped, or None if absent.

    Raises:
        ValueError: If the keyword appears more than once.
    """
    matches = re.findall(r'(?m)^ *' + keyword + r' *= *([^\r\n]*)', body)
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(f'declares {keyword} {len(matches)} times')
    return str(matches[0]).rstrip()


#===============================================================================
def _keyword_region(body: str) -> tuple[list[tuple[str, str]], str]:
    """Split a block body into its keyword lines and everything after them.

    The keyword region ends at the first DESCRIPTION line (whose quoted prose
    may span many lines and must never be scanned for keywords) or at the
    first line that is not a ``keyword = value`` line.

    Parameters:
        body: The block body.

    Returns:
        A tuple of the keyword lines -- each a (keyword, full line) pair, in
        order -- and the remaining text.
    """
    lines: list[tuple[str, str]] = []
    pos = 0
    while pos < len(body):
        match = _KEYWORD_LINE_RE.match(body, pos)
        if match is None or match.group(1) == 'DESCRIPTION':
            break
        lines.append((match.group(1), match.group(0)))
        pos = match.end()
    return lines, body[pos:]


#===============================================================================
def merge_column_definitions(template_path: object, content: str) -> str:
    """Lower every definition/stub group to plain COLUMN objects.

    Runs as a PdsTemplate preprocessor, first in the chain: each
    COLUMN_DEFINITION block is deleted, and each of its COLUMN_STUB blocks
    becomes an ordinary COLUMN carrying its own NAME, the definition's
    shippable keyword lines in the definition's order (a stub's own line wins
    where it states one), and the rest of the stub body. Private keywords
    never reach a merged column. Templates without definitions pass through
    unchanged.

    Parameters:
        template_path: The template path, unused; part of the preprocessor
            call signature.
        content: The template content.

    Returns:
        The lowered content.

    Raises:
        ValueError: If a stub appears with no preceding definition, or a
            definition is followed by no stubs.
    """
    blocks = tokenize(content)
    if not any(block.kind != 'COLUMN' for block in blocks):
        return content

    out: list[str] = []
    pos = 0
    def_lines: list[tuple[str, str]] | None = None
    def_rest = ''
    stubs_seen = 0

    for block in blocks:
        separator = content[pos:block.start]
        pos = block.end

        if block.kind == 'COLUMN_DEFINITION':
            if def_lines is not None and stubs_seen == 0:
                raise ValueError('a COLUMN_DEFINITION is followed by no '
                                 'COLUMN_STUB objects')
            out.append(separator)
            def_lines, def_rest = _keyword_region(block.body)
            stubs_seen = 0
            # The separator between the definition and its first stub is
            # swallowed with the definition itself.
            continue

        if block.kind == 'COLUMN_STUB':
            if def_lines is None:
                raise ValueError('a COLUMN_STUB appears with no preceding '
                                 'COLUMN_DEFINITION')
            if stubs_seen:
                out.append(separator)
            stub_lines, stub_rest = _keyword_region(block.body)
            out.append(_merged_column(block, def_lines, def_rest,
                                      stub_lines, stub_rest))
            stubs_seen += 1
            continue

        # A plain COLUMN passes through and ends any open group.
        if def_lines is not None and stubs_seen == 0:
            raise ValueError('a COLUMN_DEFINITION is followed by no '
                             'COLUMN_STUB objects')
        def_lines = None
        out.append(separator)
        out.append(block.header + block.body + block.footer)

    if def_lines is not None and stubs_seen == 0:
        raise ValueError('a COLUMN_DEFINITION is followed by no COLUMN_STUB '
                         'objects')
    out.append(content[pos:])
    return ''.join(out)


def _merged_column(stub: Block, def_lines: list[tuple[str, str]],
                   def_rest: str, stub_lines: list[tuple[str, str]],
                   stub_rest: str) -> str:
    """Assemble one shipped COLUMN from a stub and its definition.

    Parameters:
        stub: The stub block.
        def_lines: The definition's keyword lines, in order.
        def_rest: The definition body after its keyword lines (its
            DESCRIPTION, when it has one).
        stub_lines: The stub's keyword lines, in order.
        stub_rest: The stub body after its keyword lines.

    Returns:
        The COLUMN object's full text.
    """
    overrides = dict(stub_lines)
    consumed = set()

    lines: list[str] = []
    for keyword, line in stub_lines:
        if keyword == 'NAME':
            lines.append(line)
            consumed.add('NAME')
            break
    for keyword, line in def_lines:
        if keyword in _NOT_MERGED:
            continue
        if keyword in overrides:
            lines.append(overrides[keyword])
            consumed.add(keyword)
        else:
            lines.append(line)
    # Stub-only keywords keep their stub order; private keywords never ship.
    for keyword, line in stub_lines:
        if keyword not in consumed and keyword not in _NOT_MERGED:
            lines.append(line)
    # The stub's own trailing text (its DESCRIPTION) wins over the
    # definition's.
    rest = stub_rest if stub_rest.strip() else def_rest

    header = stub.header.replace('COLUMN_STUB', 'COLUMN')
    footer = stub.footer.replace('COLUMN_STUB', 'COLUMN')
    return header + ''.join(lines) + rest + footer
