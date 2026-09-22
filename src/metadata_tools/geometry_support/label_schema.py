################################################################################
# geometry_support/label_schema.py - Read a geometry table's schema from its label
# template.
################################################################################
"""Resolve a geometry table's column schema from its PDS3 label template.

The template is the single source of truth for a geometry column: which columns
exist, in what order, each column's width, print format, null value, valid
range, and unit -- and, through a set of private per-COLUMN keywords, how the
column is computed. This module parses all of it into the
:class:`TableSchema` that :mod:`~metadata_tools.geometry_support.prep` walks
when it builds a row.

The private keywords are ``BACKPLANE_KEY``, ``MASK``, ``VALUES``,
``OVERFLOW_FORMAT``, ``LINK_FN``, and ``LINK_ID``. They are written in the
template like any other COLUMN keyword but are not PDS3 Data Dictionary
keywords, so the label write path strips them; see
:func:`metadata_tools.label_support.create`. The right-hand side of
``BACKPLANE_KEY``, ``MASK``, and ``VALUES`` is a Python literal -- these lines
are never parsed as ODL by anything -- while ``OVERFLOW_FORMAT`` uses the same
PDS3 FORMAT notation as the FORMAT keyword and ``LINK_FN``/``LINK_ID`` hold
quoted strings.

This mirrors :class:`metadata_tools.index_support.table.IndexTable`, which
already derives its columns from its own template.

Validation is deliberately loud and happens once, when the table is
constructed, rather than silently producing a misaligned row per observation.
A template whose column declares no computation, splits a multi-value group,
or omits a null value fails the run immediately.
"""
import ast
import re
from dataclasses import dataclass
from typing import Any

from filecache import FCPath
from pdstemplate import PdsTemplate
from pdstemplate.pds3table import Pds3Table

import metadata_tools.defs as defs

# The prefix columns each table kind writes ahead of its geometry columns, in
# order. These come from Record.prefixes and prep.append_body_prefix, not from
# a backplane computation, so they are matched by name and skipped.
PREFIX_NAMES: dict[str, tuple[str, ...]] = {
    'sky':  ('VOLUME_ID', 'FILE_SPECIFICATION_NAME'),
    'ring': ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME'),
    'body': ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME', 'BODY_NAME'),
    'sun':  ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME', 'BODY_NAME'),
}

# Null keywords in priority order, matching IndexTable._get_null_value.
_NULL_KEYWORDS = ('NULL_CONSTANT', 'UNKNOWN_CONSTANT', 'INVALID_CONSTANT',
                  'MISSING_CONSTANT', 'NOT_APPLICABLE_CONSTANT')

# The private keywords carrying the computation spec. label_support strips
# exactly this set from generated labels; keep the two lists in sync.
PRIVATE_KEYWORDS = ('BACKPLANE_KEY', 'MASK', 'VALUES', 'OVERFLOW_FORMAT',
                    'LINK_FN', 'LINK_ID')

# The link functions Record.postprocess can dispatch to.
_LINK_FUNCTIONS = frozenset({'null'})

# "F12.3" -> ("F", "12", "3");  "A23" -> ("A", "23", None)
_FORMAT_RE = re.compile(r'^([FAEI])(\d+)(?:\.(\d+))?$')

# Units that PDS3 ought to recognize but does not yet.
#
# _VALID_UNITS in rms-pdstemplate transcribes the UNIT_LIST of pdsdd.full, a
# 2011 dump of a dictionary no longer curated. It carries arcsec/pixel,
# km/pixel, m/pixel and b/pixel but not deg/pixel, so the ring longitudinal
# resolutions -- which the RMS archive already ships with that unit -- would be
# rejected. SETI/rms-pdstemplate#21 adds it upstream.
#
# TEMPORARY. tests/test_geometry_schema.py fails once the installed
# rms-pdstemplate recognizes these, which is the signal to delete this set and
# raise the floor in pyproject.toml.
_PENDING_DD_UNITS = frozenset({'deg/pixel'})

# The angular unit, once any "/pixel" qualifier is stripped. Backplane values
# arrive from oops in radians, so a column tabulated in degrees needs
# converting and one tabulated in radians does not.
_DEGREES = 'deg'
_PER_PIXEL = '/pixel'


#===============================================================================
@dataclass(frozen=True)
class ColumnStub:
    """One COLUMN object's label metadata, as declared by the template.

    Attributes:
        name: The column NAME.
        width: The full field width in characters, including the enclosing
            quotes for a string column.
        print_format: The printf format producing that field.
        null_value: The value written when the column has nothing to report.
        valid_minimum: The lower bound, or None if the template declares none.
        valid_maximum: The upper bound, or None if the template declares none.
        unit: The canonical PDS3 unit, or None if the column declares none.
        flag: The conversion derived from the unit, range, and data type; see
            :func:`derive_flag`.
        overflow_format: The printf format substituted when a value will not
            fit the field, from the OVERFLOW_FORMAT keyword; None when the
            column cannot overflow.
    """

    name: str
    width: int
    print_format: str
    null_value: float | str | None
    valid_minimum: float | None
    valid_maximum: float | None
    unit: str | None = None
    flag: str = ''
    overflow_format: str | None = None


#===============================================================================
@dataclass(frozen=True)
class ResolvedColumn:
    """One computed geometry column and the label metadata of its values.

    Attributes:
        key: The backplane key passed to ``Backplane.evaluate()``. May still
            contain the ``defs.BODYX`` placeholder, substituted per body when
            the row is built.
        mask: ``(masker, shadower, face)``. The masker and shadower strings
            concatenate ``"P"`` (planet), ``"R"`` (rings), and ``"M"`` (blocker
            body); the face is ``"D"``, ``"N"``, or ``""``.
        link_fn: The link function grouping columns that go null together, or
            ``''`` when the column is unlinked.
        link_id: The token naming the column's link group, or ``''`` when
            unlinked. Its only meaning is equality: columns in one table
            sharing ``(link_fn, link_id)`` form one group.
        stubs: The label metadata for each value this column produces, in slot
            order.
    """

    key: tuple[Any, ...]
    mask: tuple[str, str, str]
    link_fn: str = ''
    link_id: str = ''
    stubs: tuple[ColumnStub, ...] = ()


#===============================================================================
@dataclass(frozen=True)
class TableSchema:
    """Everything a geometry table needs to know about its own columns.

    Attributes:
        prefix_stubs: The leading identification columns, in template order.
        columns: The geometry columns, in template order. Template order is
            output order.
    """

    prefix_stubs: tuple[ColumnStub, ...]
    columns: tuple[ResolvedColumn, ...]


#===============================================================================
@dataclass(frozen=True)
class _SpecKeywords:
    """The private computation keywords one COLUMN object carries, parsed.

    Every field is None when the template omits the keyword.
    """

    backplane_key: tuple[Any, ...] | None
    mask: tuple[str, str, str] | None
    values: int | None
    link_fn: str | None
    link_id: str | None

    def starts_group(self) -> bool:
        """Whether this column opens a computation group."""
        return self.backplane_key is not None

    def group_fields(self) -> list[str]:
        """The group-level keywords present, for error messages."""
        present = []
        if self.backplane_key is not None:
            present.append('BACKPLANE_KEY')
        if self.mask is not None:
            present.append('MASK')
        if self.values is not None:
            present.append('VALUES')
        if self.link_fn is not None:
            present.append('LINK_FN')
        if self.link_id is not None:
            present.append('LINK_ID')
        return present


#===============================================================================
@dataclass(frozen=True)
class _RawColumn:
    """One parsed COLUMN object: its label stub plus its private keywords."""

    stub: ColumnStub
    keywords: _SpecKeywords


#===============================================================================
def canonical_unit(unit: Any, name: str, template: FCPath) -> str | None:
    """Return a column's UNIT in its canonical PDS3 spelling.

    Delegates to ``rms-pdstemplate``, whose vocabulary is transcribed from the
    PDS3 Data Dictionary and which already folds case, repairs exponent style,
    and resolves the usual long forms -- DEGREES to deg, KILOMETERS to km, PIX
    to pixel. Canonicalizing here means the derivation below matches one
    spelling rather than guessing at many.

    Parameters:
        unit: The template's UNIT value, or None if it declares none.
        name: The column NAME, for the error message.
        template: The template path, for the error message.

    Returns:
        The canonical unit, or None if the column declares none.

    Raises:
        RuntimeError: If the unit is not a recognized PDS3 unit.
    """
    if unit is None:
        return None

    text = str(unit).strip().strip('"')
    if not text:
        return None

    # Private, but the alternative is transcribing the dictionary ourselves and
    # letting the two copies drift. tests/test_geometry_schema.py exercises the
    # spellings we rely on, so an upstream rename fails there rather than here.
    canonical = Pds3Table._get_valid_unit(text)
    if canonical:
        return str(canonical)
    if text in _PENDING_DD_UNITS:
        return text

    raise RuntimeError(
        f'{template}: column {name!r} declares UNIT {unit!r}, which is not a recognized '
        f'PDS3 unit. The unit decides how the column is converted, so an unrecognized '
        f'one cannot be guessed at.')


#===============================================================================
def derive_flag(unit: str | None, valid_minimum: float | None,
                valid_maximum: float | None, data_type: Any) -> str:
    """Derive a column's conversion flag from what its label declares.

    This rests on one invariant: **oops reports angles in radians and lengths in
    kilometres**. The label states the unit the column is tabulated in, so the
    conversion is exactly the difference between the two. A column in ``deg``
    needs converting; one in ``rad`` or ``km`` does not.

    A ``/pixel`` qualifier does not change that -- ``deg/pixel`` is converted
    just as ``deg`` is -- so it is stripped before the comparison.

    Cyclic coverage follows from the valid range. A quantity whose range spans
    a full circle wraps, so its extremes must be reported as angular coverage
    rather than a plain minimum and maximum; the stated range also says which
    convention, ``(0,360)`` or ``(-180,180)``. A narrower range cannot wrap, so
    it takes the ordinary minimum and maximum. The test is deliberately gated on
    an angular unit, so a dimensionless column spanning -180 to 180 is not
    mistaken for one.

    Parameters:
        unit: The canonical unit, or None.
        valid_minimum: The declared lower bound, or None.
        valid_maximum: The declared upper bound, or None.
        data_type: The declared DATA_TYPE.

    Returns:
        One of '', 'DEG', '360', '-180', or 'ISO'.
    """
    if data_type == 'TIME':
        return 'ISO'
    if unit is None:
        return ''

    base = unit[:-len(_PER_PIXEL)] if unit.endswith(_PER_PIXEL) else unit
    if base != _DEGREES:
        return ''

    if (valid_minimum is not None and valid_maximum is not None
            and valid_maximum - valid_minimum >= 360.):
        return '-180' if valid_minimum < 0. else '360'

    return 'DEG'


#===============================================================================
def _parse_format(name: str, fmt: str | None, template: FCPath) -> tuple[int, str]:
    """Convert a PDS3 FORMAT value into a field width and a printf format.

    ``F<w>.<d>`` becomes ``("%<w>.<d>f", w)``. ``A<n>`` becomes ``("%<n+2>s",
    n + 2)``: PDS counts the characters inside the quotes, while the writer
    emits the quotes as well.

    Parameters:
        name: The column NAME, for the error message.
        fmt: The template's FORMAT value.
        template: The template path, for the error message.

    Returns:
        A tuple of the field width and the printf format.

    Raises:
        RuntimeError: If FORMAT is absent or is not a form this writer emits.
    """
    if not fmt:
        raise RuntimeError(
            f'{template}: column {name!r} declares no FORMAT, so its width is '
            f'undefined. Every geometry column must declare one.')
    match = _FORMAT_RE.match(fmt.strip().strip('"'))
    if match is None:
        raise RuntimeError(f'{template}: column {name!r} has unsupported FORMAT {fmt!r}')

    code, width_text, decimals = match.groups()
    width = int(width_text)
    if code == 'A':
        # The written field is quoted; PDS BYTES counts only the contents.
        return (width + 2, f'%{width + 2}s')
    if decimals is None:
        raise RuntimeError(f'{template}: column {name!r} FORMAT {fmt!r} needs a decimal count')
    return (width, f'%{width}.{int(decimals)}{code.lower()}')


#===============================================================================
def _keyword_value(body: str, keyword: str, name: str,
                   template: FCPath) -> str | None:
    """Return the raw right-hand side of one private keyword, or None.

    The line-start anchor keeps uppercase words inside a DESCRIPTION from
    matching; the write-time strip in ``label_support`` anchors the same way,
    so the read and strip can never disagree about what is a keyword line.

    Parameters:
        body: One COLUMN object's text.
        keyword: The private keyword to read.
        name: The column NAME, for the error message.
        template: The template path, for the error message.

    Returns:
        The right-hand side, trailing whitespace stripped, or None if the
        keyword is absent.

    Raises:
        RuntimeError: If the keyword appears more than once.
    """
    matches = re.findall(r'(?m)^ *' + keyword + r' *= *([^\r\n]*)', body)
    if not matches:
        return None
    if len(matches) > 1:
        raise RuntimeError(
            f'{template}: column {name!r} declares {keyword} {len(matches)} times')
    return str(matches[0]).rstrip()


#===============================================================================
def _literal(text: str, keyword: str, name: str, template: FCPath) -> Any:
    """Evaluate one private keyword's right-hand side as a Python literal.

    Parameters:
        text: The raw right-hand side.
        keyword: The keyword, for the error message.
        name: The column NAME, for the error message.
        template: The template path, for the error message.

    Returns:
        The evaluated literal.

    Raises:
        RuntimeError: If the text is not a valid Python literal.
    """
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError) as error:
        raise RuntimeError(
            f'{template}: column {name!r} has unparseable {keyword} {text!r}: '
            f'{error}') from None


#===============================================================================
def _parse_spec_keywords(body: str, name: str, width: int,
                         template: FCPath) -> tuple[_SpecKeywords, str | None]:
    """Parse one COLUMN object's private keywords.

    Parameters:
        body: The COLUMN object's text.
        name: The column NAME, for error messages.
        width: The column's field width, from FORMAT, against which the
            overflow format is checked.
        template: The template path, for error messages.

    Returns:
        A tuple of the parsed keywords and the overflow printf format (None
        when the column declares no OVERFLOW_FORMAT).

    Raises:
        RuntimeError: If a keyword is malformed, or the overflow format does
            not fill the field exactly.
    """
    raw = {keyword: _keyword_value(body, keyword, name, template)
           for keyword in PRIVATE_KEYWORDS}

    key: tuple[Any, ...] | None = None
    if raw['BACKPLANE_KEY'] is not None:
        key = _literal(raw['BACKPLANE_KEY'], 'BACKPLANE_KEY', name, template)
        if not isinstance(key, tuple):
            raise RuntimeError(
                f'{template}: column {name!r} BACKPLANE_KEY must be a tuple, '
                f'not {key!r}')

    mask: tuple[str, str, str] | None = None
    if raw['MASK'] is not None:
        mask = _literal(raw['MASK'], 'MASK', name, template)
        if (not isinstance(mask, tuple) or len(mask) != 3
                or not all(isinstance(part, str) for part in mask)):
            raise RuntimeError(
                f'{template}: column {name!r} MASK must be a tuple of three '
                f'strings (masker, shadower, face), not {mask!r}')

    values: int | None = None
    if raw['VALUES'] is not None:
        values = _literal(raw['VALUES'], 'VALUES', name, template)
        if not isinstance(values, int) or isinstance(values, bool) or values < 1:
            raise RuntimeError(
                f'{template}: column {name!r} VALUES must be a positive integer, '
                f'not {values!r}')

    overflow_format: str | None = None
    if raw['OVERFLOW_FORMAT'] is not None:
        overflow_width, overflow_format = _parse_format(
            name, raw['OVERFLOW_FORMAT'], template)
        if overflow_width != width:
            raise RuntimeError(
                f'{template}: column {name!r} has OVERFLOW_FORMAT '
                f'{raw["OVERFLOW_FORMAT"]}, which writes {overflow_width} characters '
                f'into a {width}-character field. An overflow format must fill the '
                f'field exactly; a short one shifts every later column on the row.')

    link_fn = raw['LINK_FN']
    if link_fn is not None:
        link_fn = link_fn.strip().strip('"')
    link_id = raw['LINK_ID']
    if link_id is not None:
        link_id = link_id.strip().strip('"')

    return (_SpecKeywords(backplane_key=key, mask=mask, values=values,
                          link_fn=link_fn, link_id=link_id),
            overflow_format)


#===============================================================================
def _read_columns(template_path: FCPath) -> list[_RawColumn]:
    """Parse every COLUMN object out of a label template, in order.

    Parameters:
        template_path: Path to the host's summary label template.

    Returns:
        One raw column -- label stub plus private keywords -- per COLUMN
        object, in template order.

    Raises:
        RuntimeError: If a column's FORMAT is missing or unsupported, or a
            private keyword is malformed.
    """
    template_dir = template_path.parent
    # PdsTemplate expands $INCLUDE into .content at construction; the column
    # definitions live in the shared fragments, so this expansion is required.
    template = PdsTemplate(template_path, crlf=True,
                           includes=[defs.GLOBAL_TEMPLATE_PATH, template_dir])
    # Pds3Table stores itself in a pdstemplate module global. Parse only at
    # table construction, never between a label's PdsTemplate construction and
    # its write, or the write path's own analysis would be displaced.
    pds3 = Pds3Table(template_path, template.content, validate=False, analyze_only=True)

    # The same regex Pds3Table splits on, so this enumeration can never
    # disagree with old_lookup's column numbering; the count is asserted below.
    bodies = Pds3Table._OBJECT_COLUMN_REGEX.split(template.content)[2::4]

    columns: list[_RawColumn] = []
    colnum = 1
    while True:
        try:
            name = pds3.old_lookup('NAME', colnum)
        except IndexError:
            break

        null: Any = None
        for keyword in _NULL_KEYWORDS:
            value = pds3.old_lookup(keyword, colnum)
            # Compared against None rather than tested for truth: a null of 0
            # or "" is a legitimate declaration, and the index pipeline's
            # equivalent loop drops both.
            if value is not None:
                null = value
                break

        column_name = str(name).strip().strip('"')
        width, print_format = _parse_format(column_name, pds3.old_lookup('FORMAT', colnum),
                                            template_path)
        valid_minimum = pds3.old_lookup('VALID_MINIMUM', colnum)
        valid_maximum = pds3.old_lookup('VALID_MAXIMUM', colnum)
        data_type = pds3.old_lookup('DATA_TYPE', colnum)
        unit = canonical_unit(pds3.old_lookup('UNIT', colnum), column_name, template_path)
        keywords, overflow_format = _parse_spec_keywords(
            bodies[colnum - 1], column_name, width, template_path)
        stub = ColumnStub(name=column_name,
                          width=width,
                          print_format=print_format,
                          null_value=null,
                          valid_minimum=valid_minimum,
                          valid_maximum=valid_maximum,
                          unit=unit,
                          flag=derive_flag(unit, valid_minimum, valid_maximum,
                                           data_type),
                          overflow_format=overflow_format)
        columns.append(_RawColumn(stub=stub, keywords=keywords))
        colnum += 1

    if len(bodies) != len(columns):
        raise RuntimeError(
            f'{template_path}: the private-keyword pass found {len(bodies)} COLUMN '
            f'objects but Pds3Table found {len(columns)}; the two parsers have '
            f'diverged')

    return columns


#===============================================================================
def template_name_for(template_dir: FCPath, qualifier: str) -> str:
    """Return the file name of a host's summary template for one table kind.

    The write path reaches the same name from the other direction, by
    substituting the collection name into a table's file name; see
    :func:`metadata_tools.util.get_template_name`. Both derivations are pinned
    against each other by ``tests/test_geometry_schema.py`` so the read and
    write paths cannot drift apart.

    Parameters:
        template_dir: The host's ``templates/`` directory.
        qualifier: ``'sky'``, ``'sun'``, ``'ring'``, or ``'body'``.

    Returns:
        The template file name, e.g. ``'GO_0xxx_body_summary.lbl'``.
    """
    return f'{template_dir.parent.name}_{qualifier}_summary.lbl'


#===============================================================================
_schema_cache: dict[tuple[str, str], TableSchema] = {}


def resolve_schema(template_dir: str | FCPath, qualifier: str) -> TableSchema:
    """Resolve one geometry table's column schema from its label template.

    Parses the host's summary template, skips the fixed prefix columns, and
    groups the remaining COLUMN objects into computations: a column carrying
    ``BACKPLANE_KEY`` opens a group and absorbs the following ``VALUES - 1``
    columns as its remaining slots. Template order is output order.

    The result is cached per (template directory, qualifier).

    Parameters:
        template_dir: The host's ``templates/`` directory.
        qualifier: ``'sky'``, ``'sun'``, ``'ring'``, or ``'body'``.

    Returns:
        The resolved schema.

    Raises:
        RuntimeError: If the prefix columns do not match or carry a private
            keyword, a data column neither opens a group nor is absorbed by
            one, an absorbed column carries a group-level keyword, a group
            runs past the end of the table, only one of LINK_FN and LINK_ID is
            given, LINK_FN is not a known link function, a group's parts
            derive different conversions, a column declares no null value or
            an unrecognized unit, a column declares an empty valid range, or
            an overflow format does not fill its field.
    """
    template_dir = FCPath(template_dir)
    cache_key = (template_dir.as_posix(), qualifier)
    if cache_key in _schema_cache:
        return _schema_cache[cache_key]

    template_path = template_dir / template_name_for(template_dir, qualifier)
    raws = _read_columns(template_path)

    # Consume the fixed prefix run.
    expected = PREFIX_NAMES[qualifier]
    found = tuple(raw.stub.name for raw in raws[:len(expected)])
    if found != expected:
        raise RuntimeError(
            f'{template_path}: the {qualifier} table must begin with the prefix columns '
            f'{expected}, but the template begins with {found}')
    for raw in raws[:len(expected)]:
        present = raw.keywords.group_fields()
        if raw.stub.overflow_format is not None:
            present.append('OVERFLOW_FORMAT')
        if present:
            raise RuntimeError(
                f'{template_path}: prefix column {raw.stub.name!r} carries the private '
                f'keyword(s) {present}; prefix columns are not computed')
    prefix_stubs = tuple(raw.stub for raw in raws[:len(expected)])
    data = raws[len(expected):]

    for raw in data:
        if raw.stub.name in expected:
            raise RuntimeError(
                f'{template_path}: prefix column {raw.stub.name!r} reappears among the '
                f'geometry columns')

    columns: list[ResolvedColumn] = []
    index = 0
    while index < len(data):
        raw = data[index]
        keywords = raw.keywords
        if not keywords.starts_group():
            raise RuntimeError(
                f'{template_path}: column {raw.stub.name!r} has no BACKPLANE_KEY and is '
                f'not absorbed by a preceding column, so nothing knows how to compute '
                f'it. Give it a BACKPLANE_KEY, or raise the VALUES of the column it '
                f'belongs to.')

        values = keywords.values if keywords.values is not None else 1
        group = data[index:index + values]
        if len(group) < values:
            raise RuntimeError(
                f'{template_path}: column {raw.stub.name!r} declares VALUES = {values}, '
                f'which runs past the end of the table')

        for member in group[1:]:
            present = member.keywords.group_fields()
            if present:
                raise RuntimeError(
                    f'{template_path}: column {member.stub.name!r} carries {present} but '
                    f'is value {group.index(member) + 1} of the column starting at '
                    f'{raw.stub.name!r}. Group-level keywords belong on the first '
                    f'column only.')

        if (keywords.link_fn is None) != (keywords.link_id is None):
            raise RuntimeError(
                f'{template_path}: column {raw.stub.name!r} declares only one of '
                f'LINK_FN and LINK_ID; they must be given together or not at all')
        if keywords.link_fn is not None and keywords.link_fn not in _LINK_FUNCTIONS:
            raise RuntimeError(
                f'{template_path}: column {raw.stub.name!r} declares LINK_FN '
                f'{keywords.link_fn!r}, which is not a known link function; known '
                f'functions are {sorted(_LINK_FUNCTIONS)}')

        flags = {member.stub.flag for member in group}
        if len(flags) > 1:
            raise RuntimeError(
                f'{template_path}: the parts of column {raw.stub.name!r} derive '
                f'different conversions {sorted(flags)} from their labels. All parts '
                f'of a column must declare the same UNIT and valid range.')

        for member in group:
            if member.stub.null_value is None:
                raise RuntimeError(
                    f'{template_path}: column {member.stub.name!r} declares no null '
                    f'value. Add NULL_CONSTANT; the pipeline writes one whenever the '
                    f'column has nothing to report.')
            if (member.stub.valid_minimum is not None
                    and member.stub.valid_minimum == member.stub.valid_maximum):
                raise RuntimeError(
                    f'{template_path}: column {member.stub.name!r} declares an empty '
                    f'valid range (VALID_MINIMUM == VALID_MAXIMUM == '
                    f'{member.stub.valid_minimum}), which would null every value. Omit '
                    f'both to skip the range check.')

        columns.append(ResolvedColumn(key=keywords.backplane_key or (),
                                      mask=keywords.mask or ('', '', ''),
                                      link_fn=keywords.link_fn or '',
                                      link_id=keywords.link_id or '',
                                      stubs=tuple(member.stub for member in group)))
        index += values

    schema = TableSchema(prefix_stubs=prefix_stubs, columns=tuple(columns))
    _schema_cache[cache_key] = schema
    return schema
