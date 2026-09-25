################################################################################
# column_grammar.py - The definition/stub column grammar of geometry templates.
################################################################################
"""The definition/stub grammar shared by the template read and write paths.

A geometry summary template declares each computed column as a *group*: one
``OBJECT = COLUMN_DEFINITION`` block carrying the computation spec, the label
metadata shared by the group's values, and the shared lead-in DESCRIPTION,
followed by one ``OBJECT = COLUMN_STUB`` block per value, carrying its NAME,
any keyword it overrides, and its own DESCRIPTION, which the lowering appends
to the definition's. A single-valued column is simply a plain ``COLUMN``
carrying its own spec keywords, which the lowering removes in place. A
``COLUMN_DEFINITION`` therefore exists only to share metadata across a
multi-value group; one with no stubs is an error.

A column need not spell out its label format keywords. A *format dictionary*
of ``OBJECT = COLUMN_FORMAT`` entries, each a NAME and a bundle of format
keywords (FORMAT, UNIT, the null and valid-range keywords, ...), lets any
column block state ``COLUMN_FORMAT = "<entry>"`` instead; a keyword the block
states itself wins over the entry's. :func:`expand_format_references` replaces
each reference with the entry's lines and removes the entries, and runs first
on both the read and the write path, so everything downstream sees explicit
keywords only.

None of these block types is PDS3:
the write path lowers every group to plain ``COLUMN`` objects (see
:func:`merge_column_definitions`) before a label is generated, and the schema
reader
(:mod:`metadata_tools.geometry_support.label_schema`) parses the grammar
directly.

This module is deliberately light -- regular expressions and text
manipulation only -- so :mod:`metadata_tools.label_support` can import it
without touching the geometry engine.
"""
import re
import textwrap
from dataclasses import dataclass

# The private keywords: the computation spec, allowed only on a
# COLUMN_DEFINITION or a self-contained plain COLUMN (OVERFLOW_FORMAT may also
# appear on a stub as an override), and COLUMN_FORMAT, the format-dictionary
# reference, which expansion always consumes. label_support strips exactly
# this set from generated labels; tests pin the two against each other.
PRIVATE_KEYWORDS = ('BACKPLANE_KEY', 'MASK', 'OVERFLOW_FORMAT', 'LINK_FN',
                    'LINK_ID', 'COLUMN_FORMAT')

# The keywords a COLUMN_FORMAT entry may carry besides its NAME: label format
# metadata only. Nothing else -- not a DESCRIPTION, a computation spec
# keyword, or another COLUMN_FORMAT -- belongs in a shared format.
FORMAT_ENTRY_KEYWORDS = frozenset({
    'DATA_TYPE', 'FORMAT', 'OVERFLOW_FORMAT', 'UNIT',
    'NULL_CONSTANT', 'UNKNOWN_CONSTANT', 'INVALID_CONSTANT',
    'MISSING_CONSTANT', 'NOT_APPLICABLE_CONSTANT',
    'VALID_MINIMUM', 'VALID_MAXIMUM'})

# Keywords that never reach a merged COLUMN: the private set, the retired
# VALUES keyword (group size is now the stub count), and NAME, which every
# stub states for itself.
_NOT_MERGED = frozenset(PRIVATE_KEYWORDS) | {'VALUES', 'NAME'}

# One OBJECT block of any of the four column-grammar kinds. The alternation
# tries the longer names first, and the END_OBJECT backreference guarantees
# the opening and closing kinds agree.
_BLOCK_RE = re.compile(
    r'(?<![ \w])( *OBJECT *= *(COLUMN_DEFINITION|COLUMN_FORMAT|COLUMN_STUB|COLUMN)'
    r' *\r?\n)'
    r'(.*?\r?\n)'
    r'( *END_OBJECT *= *\2 *\r?\n)', re.DOTALL)

# A stray opener that _BLOCK_RE did not consume (e.g. mismatched END_OBJECT).
_STRAY_OBJECT_RE = re.compile(
    r'(?m)^ *OBJECT *= *(COLUMN_DEFINITION|COLUMN_FORMAT|COLUMN_STUB|COLUMN) *\r?$')

# A spec keyword line (the retired VALUES included), for removal from plain
# COLUMN objects at lowering time.
_PRIVATE_LINE_RE = re.compile(
    r'(?m)^ *(' + '|'.join(PRIVATE_KEYWORDS + ('VALUES',)) + r') *=[^\r\n]*\r?\n')

# One "keyword = value" line, including its terminator. Matched with
# .match(body, pos) where pos is always a line start, so no ^ anchor (which
# would assert the start of the whole string, not of the line at pos).
_KEYWORD_LINE_RE = re.compile(r' *([A-Z][A-Z0-9_]*) *=[^\r\n]*\r?\n')


#===============================================================================
@dataclass(frozen=True)
class Block:
    """One tokenized OBJECT block of the column grammar.

    Attributes:
        kind: ``'COLUMN'``, ``'COLUMN_DEFINITION'``, ``'COLUMN_STUB'``, or
            ``'COLUMN_FORMAT'``.
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
def tokenize(content: str, *, allow_formats: bool = False) -> list[Block]:
    """Split template content into its column-grammar blocks, in order.

    Parameters:
        content: The template text, includes expanded.
        allow_formats: If True, format-dictionary entries and references are
            returned like any other block. Only
            :func:`expand_format_references` passes True; every other caller
            must see expanded content, so an entry or reference reaching it
            is an error rather than a silently unexpanded column.

    Returns:
        The blocks, in template order.

    Raises:
        ValueError: If an OBJECT opener of a column kind is not part of a
            well-formed block -- which otherwise would be silently skipped --
            or, unless allow_formats is True, if a COLUMN_FORMAT entry or a
            COLUMN_FORMAT reference is present.
    """
    blocks = []
    pos = 0
    for match in _BLOCK_RE.finditer(content):
        _check_no_stray_object(content[pos:match.start()])
        # A mistyped END_OBJECT lets the lazy body run on to a later block's
        # matching footer; an opener inside the body exposes that.
        _check_no_stray_object(match.group(3))
        block = Block(kind=match.group(2), header=match.group(1),
                      body=match.group(3), footer=match.group(4),
                      start=match.start(), end=match.end())
        if not allow_formats:
            _check_expanded(block)
        blocks.append(block)
        pos = match.end()
    _check_no_stray_object(content[pos:])
    return blocks


def _check_expanded(block: Block) -> None:
    """Reject a format-dictionary entry or reference in expanded content.

    Parameters:
        block: A tokenized block.

    Raises:
        ValueError: If the block is a COLUMN_FORMAT entry or carries a
            COLUMN_FORMAT reference.
    """
    if block.kind == 'COLUMN_FORMAT':
        raise ValueError('a COLUMN_FORMAT entry was never expanded; run '
                         'expand_format_references first')
    lines, _ = _keyword_region(block.body)
    if any(keyword == 'COLUMN_FORMAT' for keyword, _ in lines):
        raise ValueError('a COLUMN_FORMAT reference was never expanded; run '
                         'expand_format_references first')


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
def expand_format_references(template_path: object, content: str) -> str:
    """Expand every format-dictionary reference and remove the dictionary.

    Runs first, ahead of :func:`merge_column_definitions` on the write path
    and ahead of the schema read, so everything downstream sees explicit
    keywords only. Each ``COLUMN_FORMAT`` entry is removed from the content.
    In every other block, a ``COLUMN_FORMAT = "<entry>"`` line in the keyword
    region is replaced by the entry's keyword lines, in the entry's order and
    re-indented to the reference, minus any keyword the block states itself:
    a column's own keyword always wins over its entry's. On a stub, the
    expanded lines are the stub's own, so they override the definition's in
    the lowering exactly as hand-written ones would. Content with neither
    entries nor references passes through unchanged.

    Parameters:
        template_path: The template path, unused; part of the preprocessor
            call signature.
        content: The template content, includes expanded.

    Returns:
        The expanded content.

    Raises:
        ValueError: If an entry is malformed or duplicated, or a reference is
            repeated, misplaced, or names no entry.
    """
    if 'COLUMN_FORMAT' not in content:
        return content

    blocks = tokenize(content, allow_formats=True)
    entries: dict[str, list[tuple[str, str]]] = {}
    for block in blocks:
        if block.kind == 'COLUMN_FORMAT':
            name, lines = _format_entry(block)
            if name in entries:
                raise ValueError(f'format entry {name!r} is defined twice')
            entries[name] = lines

    out: list[str] = []
    pos = 0
    for block in blocks:
        separator = content[pos:block.start]
        pos = block.end
        if block.kind == 'COLUMN_FORMAT':
            # An entry goes with the blank lines before it; any other text
            # there (a $NOTE, say) stays.
            if separator.strip():
                out.append(separator)
            continue
        out.append(separator)
        out.append(_expand_block(block, entries))
    out.append(content[pos:])
    return ''.join(out)


def _format_entry(block: Block) -> tuple[str, list[tuple[str, str]]]:
    """Validate one COLUMN_FORMAT entry and return its name and lines.

    Parameters:
        block: The entry block.

    Returns:
        A tuple of the entry NAME and its keyword lines, NAME excluded, each a
        (keyword, full line) pair in order.

    Raises:
        ValueError: If the entry has no NAME, holds anything but keyword
            lines, repeats a keyword, carries a keyword that is not label
            format metadata, or carries none at all.
    """
    lines, rest = _keyword_region(block.body)
    names = [line for keyword, line in lines if keyword == 'NAME']
    if len(names) != 1:
        raise ValueError('a COLUMN_FORMAT entry must declare exactly one NAME')
    name = names[0].split('=', 1)[1].strip().strip('"')
    if rest.strip():
        raise ValueError(f'format entry {name!r} may hold only keyword lines; '
                         f'a description belongs on the column')

    keyword_lines: list[tuple[str, str]] = []
    seen: set[str] = set()
    for keyword, line in lines:
        if keyword == 'NAME':
            continue
        if keyword not in FORMAT_ENTRY_KEYWORDS:
            raise ValueError(
                f'format entry {name!r} carries {keyword}, which is not label '
                f'format metadata; allowed are {sorted(FORMAT_ENTRY_KEYWORDS)}')
        if keyword in seen:
            raise ValueError(f'format entry {name!r} declares {keyword} twice')
        seen.add(keyword)
        keyword_lines.append((keyword, line))
    if not keyword_lines:
        raise ValueError(f'format entry {name!r} declares no keywords')
    return name, keyword_lines


def _expand_block(block: Block, entries: dict[str, list[tuple[str, str]]]) -> str:
    """Return one block's text with its format reference, if any, expanded.

    Parameters:
        block: A block other than a COLUMN_FORMAT entry.
        entries: The format dictionary, by entry NAME.

    Returns:
        The block's full text.

    Raises:
        ValueError: If the block repeats its reference, places it after its
            DESCRIPTION, or names no entry.
    """
    lines, rest = _keyword_region(block.body)
    references = [line for keyword, line in lines if keyword == 'COLUMN_FORMAT']
    if not references:
        # keyword_value also rejects a second, misplaced reference below.
        if keyword_value(block.body, 'COLUMN_FORMAT') is not None:
            raise ValueError(f'column {_name_of(lines)!r} places COLUMN_FORMAT '
                             f'after its DESCRIPTION; it belongs with the '
                             f'other keywords')
        return block.header + block.body + block.footer
    if len(references) > 1 or keyword_value(rest, 'COLUMN_FORMAT') is not None:
        raise ValueError(f'column {_name_of(lines)!r} declares COLUMN_FORMAT '
                         f'more than once')

    reference = references[0]
    name = reference.split('=', 1)[1].strip().strip('"')
    if name not in entries:
        raise ValueError(f'column {_name_of(lines)!r} refers to format entry '
                         f'{name!r}, which is not defined; known entries are '
                         f'{sorted(entries)}')

    stated = {keyword for keyword, _ in lines}
    indent = reference[:len(reference) - len(reference.lstrip(' '))]
    expanded: list[str] = []
    for keyword, line in lines:
        if keyword != 'COLUMN_FORMAT':
            expanded.append(line)
            continue
        expanded.extend(indent + entry_line.lstrip(' ')
                        for entry_keyword, entry_line in entries[name]
                        if entry_keyword not in stated)
    return block.header + ''.join(expanded) + rest + block.footer


def _name_of(lines: list[tuple[str, str]]) -> str:
    """Return the unquoted NAME among a block's keyword lines, for messages.

    Parameters:
        lines: The block's keyword lines.

    Returns:
        The NAME, or ``'?'`` when the block states none.
    """
    for keyword, line in lines:
        if keyword == 'NAME':
            return line.split('=', 1)[1].strip().strip('"')
    return '?'


#===============================================================================
def merge_column_definitions(template_path: object, content: str) -> str:
    """Lower every definition/stub group to plain COLUMN objects.

    Runs as a PdsTemplate preprocessor, first in the chain: each
    COLUMN_DEFINITION block is deleted, and each of its COLUMN_STUB blocks
    becomes an ordinary COLUMN carrying its own NAME, the definition's
    shippable keyword lines in the definition's order (a stub's own line wins
    where it states one), and the rest of the stub body. A plain COLUMN --
    a prefix column, or a self-contained single-valued column -- passes
    through with any spec keyword lines removed. Private keywords never
    reach a merged column. Templates without definitions pass through
    unchanged.

    Parameters:
        template_path: The template path, unused; part of the preprocessor
            call signature.
        content: The template content.

    Returns:
        The lowered content.

    Raises:
        ValueError: If a stub appears with no preceding definition, or a
            definition is followed by no stubs (a single-valued column is a
            plain COLUMN).
    """
    blocks = tokenize(content)
    if not any(block.kind != 'COLUMN' for block in blocks):
        return content

    out: list[str] = []
    pos = 0
    pending: Block | None = None
    def_lines: list[tuple[str, str]] = []
    def_rest = ''
    stubs_seen = 0

    def check_no_stubless() -> None:
        """Reject a pending definition that gathered no stubs."""
        nonlocal pending
        if pending is not None and stubs_seen == 0:
            raise ValueError(
                'a COLUMN_DEFINITION is followed by no COLUMN_STUB objects; a '
                'single-valued column is a plain COLUMN')
        pending = None

    for block in blocks:
        separator = content[pos:block.start]
        pos = block.end

        if block.kind == 'COLUMN_DEFINITION':
            check_no_stubless()
            out.append(separator)
            pending = block
            def_lines, def_rest = _keyword_region(block.body)
            stubs_seen = 0
            # The separator between the definition and its first stub is
            # swallowed with the definition itself.
            continue

        if block.kind == 'COLUMN_STUB':
            if pending is None and stubs_seen == 0:
                raise ValueError('a COLUMN_STUB appears with no preceding '
                                 'COLUMN_DEFINITION')
            if stubs_seen:
                out.append(separator)
            else:
                pending = None
            stub_lines, stub_rest = _keyword_region(block.body)
            out.append(_merged_column(block, def_lines, def_rest,
                                      stub_lines, stub_rest))
            stubs_seen += 1
            continue

        # A plain COLUMN passes through, minus any spec keyword lines, and
        # ends any open group.
        check_no_stubless()
        stubs_seen = 0
        out.append(separator)
        out.append(block.header + _PRIVATE_LINE_RE.sub('', block.body)
                   + block.footer)

    check_no_stubless()
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
    # Descriptions compose: the definition's is the shared lead-in, the
    # stub's continues it with the per-value prose. Either may stand alone.
    if stub_rest.strip() and def_rest.strip():
        rest = _compose_description(def_rest, stub_rest)
    elif stub_rest.strip():
        rest = stub_rest
    else:
        rest = def_rest

    header = stub.header.replace('COLUMN_STUB', 'COLUMN')
    footer = stub.footer.replace('COLUMN_STUB', 'COLUMN')
    return header + ''.join(lines) + rest + footer


def _compose_description(def_rest: str, stub_rest: str) -> str:
    """Append a stub's DESCRIPTION to its definition's.

    The definition's text ships verbatim, minus its closing quote; the stub's
    payload follows after a blank line, each prose paragraph re-flowed to the
    house style (six-space indent, 78 columns) so the shipped wrap does not
    depend on how the stub happened to be wrapped around its own DESCRIPTION
    opener. A paragraph carrying a ``$`` template directive (an ``$INCLUDE``
    of shared detail text) ships verbatim instead.

    Parameters:
        def_rest: The definition's description region.
        stub_rest: The stub's description region.

    Returns:
        The composed description region.

    Raises:
        ValueError: If the stub's description does not start with the usual
            opener.
    """
    # A self-contained definition description ends with its closing quote,
    # which the composition removes; one whose last paragraph is a template
    # directive (an $INCLUDE of shared prose) has no quote of its own.
    head = def_rest.rstrip()
    if head.endswith('"'):
        head = head[:-1].rstrip()

    opener = re.match(r' *DESCRIPTION *= *"', stub_rest)
    if opener is None:
        raise ValueError(
            "a stub's DESCRIPTION must start with the usual 'DESCRIPTION = \"' "
            'opener')
    payload = stub_rest[opener.end():]

    pieces: list[str] = []
    for paragraph in re.split(r'\n[ \t]*\n', payload.rstrip('\n')):
        if '$' in paragraph:
            pieces.append(paragraph)
        else:
            text = re.sub(r'\s+', ' ', paragraph).strip()
            pieces.append('\n'.join(textwrap.wrap(
                text, width=78, initial_indent='      ',
                subsequent_indent='      ', break_on_hyphens=False)))
    return head + '\n\n' + '\n\n'.join(pieces) + '\n'
