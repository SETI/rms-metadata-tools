################################################################################
# geometry_support/label_schema.py - Read a geometry table's schema from its label
# template.
################################################################################
"""Resolve a geometry table's column schema from its PDS3 label template.

The template is the single source of truth for a geometry column, declared in
the definition/stub grammar of :mod:`metadata_tools.column_grammar`: each
computed column is one ``COLUMN_DEFINITION`` block -- carrying the backplane
key, mask, link fields, and the label metadata shared by the column's values
-- followed by one ``COLUMN_STUB`` block per value, each carrying its NAME,
its DESCRIPTION, and any keyword it overrides. Group size is the stub count;
there is no way to assimilate a column by miscounting, because membership is
declared by the stub's own object type.

The spec keywords (``BACKPLANE_KEY``, ``MASK``, ``LINK_FN``, ``LINK_ID``, and
``OVERFLOW_FORMAT``) are not PDS3 keywords, and neither are the definition
and stub blocks themselves: the label write path lowers every group to plain
``COLUMN`` objects and drops the spec keywords (see
:func:`metadata_tools.column_grammar.merge_column_definitions` and
:func:`metadata_tools.label_support.create`), so none of it reaches a shipped
label. The right-hand side of ``BACKPLANE_KEY`` and ``MASK`` is a Python
literal -- these lines are never parsed as ODL by anything -- while
``OVERFLOW_FORMAT`` uses the same PDS3 FORMAT notation as the FORMAT keyword
and ``LINK_FN``/``LINK_ID`` hold quoted strings.

This mirrors :class:`metadata_tools.index_support.table.IndexTable`, which
already derives its columns from its own template.

Validation is deliberately loud and happens once, when the table is
constructed, rather than silently producing a misaligned row per observation.
A stub with no definition, a definition with no stubs, or a column that omits
its null value fails the run immediately.
"""
import ast
import re
from dataclasses import dataclass
from typing import Any

from filecache import FCPath
from pdstemplate import PdsTemplate
from pdstemplate.pds3table import Pds3Table

import metadata_tools.defs as defs
from metadata_tools import column_grammar

# Re-exported: tests and callers reach the keyword set through this module.
from metadata_tools.column_grammar import PRIVATE_KEYWORDS as PRIVATE_KEYWORDS

# The prefix columns each table kind writes ahead of its geometry columns, in
# order. These come from Record.prefixes and prep.append_body_prefix, not from
# a backplane computation, so they stay plain COLUMN objects in the host
# template and are matched by name.
PREFIX_NAMES: dict[str, tuple[str, ...]] = {
    'sky':  ('VOLUME_ID', 'FILE_SPECIFICATION_NAME'),
    'ring': ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME'),
    'body': ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME', 'BODY_NAME'),
    'sun':  ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME', 'BODY_NAME'),
}

# Null keywords in priority order, matching IndexTable._get_null_value.
_NULL_KEYWORDS = ('NULL_CONSTANT', 'UNKNOWN_CONSTANT', 'INVALID_CONSTANT',
                  'MISSING_CONSTANT', 'NOT_APPLICABLE_CONSTANT')

# The keywords only a COLUMN_DEFINITION may carry. OVERFLOW_FORMAT is not
# among them: it is format metadata, so a stub may override it like FORMAT.
_DEFINITION_ONLY = ('BACKPLANE_KEY', 'MASK', 'LINK_FN', 'LINK_ID')

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
    """One shipped column's label metadata, as declared by the template.

    Each field is the *effective* value: the stub's own declaration when it
    states one, else its definition's.

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
    match = _FORMAT_RE.match(str(fmt).strip().strip('"'))
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
class _BlockView:
    """Effective-keyword access to one stub (or plain column) and its definition."""

    def __init__(self, body: str, definition_body: str | None, name: str,
                 template: FCPath) -> None:
        """Bind one block body, and optionally its definition's, for lookups.

        Parameters:
            body: The stub's (or plain column's) block body.
            definition_body: The definition's block body, or None for a plain
                column.
            name: The block's NAME, for error messages.
            template: The template path, for error messages.
        """
        self._bodies = [body] if definition_body is None else [body, definition_body]
        self._name = name
        self._template = template

    def raw(self, keyword: str) -> str | None:
        """The keyword's raw right-hand side: the stub's, else the definition's.

        Parameters:
            keyword: The keyword to read.

        Returns:
            The raw value, or None when neither block states it.

        Raises:
            RuntimeError: If either block declares the keyword twice.
        """
        for body in self._bodies:
            try:
                value = column_grammar.keyword_value(body, keyword)
            except ValueError as error:
                raise RuntimeError(
                    f'{self._template}: column {self._name!r} {error}') from None
            if value is not None:
                return value
        return None

    def value(self, keyword: str) -> Any:
        """The keyword's evaluated value -- quotes stripped, numbers numeric.

        Uses ``Pds3Table._eval``, the same evaluation the write path applies,
        so 'NA' arrives unquoted and -999. arrives as a float. Private, but
        pinned by the real-template tests.

        Parameters:
            keyword: The keyword to read.

        Returns:
            The evaluated value, or None when absent.
        """
        raw = self.raw(keyword)
        if raw is None:
            return None
        return Pds3Table._eval(raw)


#===============================================================================
def _literal(text: str, keyword: str, name: str, template: FCPath) -> Any:
    """Evaluate one spec keyword's right-hand side as a Python literal.

    Parameters:
        text: The raw right-hand side.
        keyword: The keyword, for the error message.
        name: The definition NAME, for the error message.
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
def _block_name(block: 'column_grammar.Block', template: FCPath) -> str:
    """Return a block's NAME, unquoted.

    Parameters:
        block: The block.
        template: The template path, for the error message.

    Returns:
        The NAME.

    Raises:
        RuntimeError: If the block declares no NAME.
    """
    try:
        name = column_grammar.keyword_value(block.body, 'NAME')
    except ValueError as error:
        raise RuntimeError(f'{template}: a {block.kind} object {error}') from None
    if name is None:
        raise RuntimeError(f'{template}: a {block.kind} object declares no NAME')
    return name.strip().strip('"')


#===============================================================================
def _make_stub(view: _BlockView, name: str, template: FCPath) -> ColumnStub:
    """Build one column's label metadata from its effective keywords.

    Parameters:
        view: The effective-keyword view of the stub and its definition.
        name: The column NAME.
        template: The template path, for error messages.

    Returns:
        The stub.

    Raises:
        RuntimeError: If FORMAT is missing or unsupported, the unit is
            unrecognized, or the overflow format does not fill the field.
    """
    width, print_format = _parse_format(name, view.raw('FORMAT'), template)

    null: Any = None
    for keyword in _NULL_KEYWORDS:
        value = view.value(keyword)
        # Compared against None rather than tested for truth: a null of 0
        # or "" is a legitimate declaration, and the index pipeline's
        # equivalent loop drops both.
        if value is not None:
            null = value
            break

    valid_minimum = view.value('VALID_MINIMUM')
    valid_maximum = view.value('VALID_MAXIMUM')
    data_type = view.value('DATA_TYPE')
    unit = canonical_unit(view.raw('UNIT'), name, template)

    overflow_format: str | None = None
    overflow_raw = view.raw('OVERFLOW_FORMAT')
    if overflow_raw is not None:
        overflow_width, overflow_format = _parse_format(name, overflow_raw, template)
        if overflow_width != width:
            raise RuntimeError(
                f'{template}: column {name!r} has OVERFLOW_FORMAT {overflow_raw}, '
                f'which writes {overflow_width} characters into a {width}-character '
                f'field. An overflow format must fill the field exactly; a short one '
                f'shifts every later column on the row.')

    return ColumnStub(name=name,
                      width=width,
                      print_format=print_format,
                      null_value=null,
                      valid_minimum=valid_minimum,
                      valid_maximum=valid_maximum,
                      unit=unit,
                      flag=derive_flag(unit, valid_minimum, valid_maximum, data_type),
                      overflow_format=overflow_format)


#===============================================================================
def _resolve_group(definition: 'column_grammar.Block',
                   stubs: 'list[column_grammar.Block]',
                   template: FCPath) -> ResolvedColumn:
    """Resolve one definition and its stubs into a column.

    Parameters:
        definition: The COLUMN_DEFINITION block.
        stubs: Its COLUMN_STUB blocks, in order.
        template: The template path, for error messages.

    Returns:
        The resolved column.

    Raises:
        RuntimeError: On any malformed group; see :func:`resolve_schema`.
    """
    def_name = _block_name(definition, template)
    def_view = _BlockView(definition.body, None, def_name, template)

    if not stubs:
        raise RuntimeError(
            f'{template}: definition {def_name!r} is followed by no COLUMN_STUB '
            f'objects, so it defines nothing')
    if len(stubs) > 2:
        raise RuntimeError(
            f'{template}: definition {def_name!r} has {len(stubs)} stubs, but no '
            f'computation produces more than two values. (Relax this check when '
            f'one does.)')

    key_raw = def_view.raw('BACKPLANE_KEY')
    if key_raw is None:
        raise RuntimeError(
            f'{template}: definition {def_name!r} declares no BACKPLANE_KEY, so '
            f'nothing knows how to compute its columns')
    key = _literal(key_raw, 'BACKPLANE_KEY', def_name, template)
    if not isinstance(key, tuple):
        raise RuntimeError(
            f'{template}: definition {def_name!r} BACKPLANE_KEY must be a tuple, '
            f'not {key!r}')

    mask: tuple[str, str, str] = ('', '', '')
    mask_raw = def_view.raw('MASK')
    if mask_raw is not None:
        mask = _literal(mask_raw, 'MASK', def_name, template)
        if (not isinstance(mask, tuple) or len(mask) != 3
                or not all(isinstance(part, str) for part in mask)):
            raise RuntimeError(
                f'{template}: definition {def_name!r} MASK must be a tuple of three '
                f'strings (masker, shadower, face), not {mask!r}')

    link_fn = def_view.raw('LINK_FN')
    link_id = def_view.raw('LINK_ID')
    if (link_fn is None) != (link_id is None):
        raise RuntimeError(
            f'{template}: definition {def_name!r} declares only one of LINK_FN and '
            f'LINK_ID; they must be given together or not at all')
    if link_fn is not None:
        link_fn = link_fn.strip().strip('"')
        link_id = str(link_id).strip().strip('"')
        if link_fn not in _LINK_FUNCTIONS:
            raise RuntimeError(
                f'{template}: definition {def_name!r} declares LINK_FN {link_fn!r}, '
                f'which is not a known link function; known functions are '
                f'{sorted(_LINK_FUNCTIONS)}')

    column_stubs: list[ColumnStub] = []
    for stub_block in stubs:
        stub_name = _block_name(stub_block, template)
        for keyword in _DEFINITION_ONLY:
            if column_grammar.keyword_value(stub_block.body, keyword) is not None:
                raise RuntimeError(
                    f'{template}: stub {stub_name!r} carries {keyword}, which '
                    f'belongs on its COLUMN_DEFINITION')
        view = _BlockView(stub_block.body, definition.body, stub_name, template)
        column_stubs.append(_make_stub(view, stub_name, template))

    flags = {stub.flag for stub in column_stubs}
    if len(flags) > 1:
        raise RuntimeError(
            f'{template}: the stubs of definition {def_name!r} derive different '
            f'conversions {sorted(flags)} from their labels. All values of a column '
            f'must share one UNIT and valid range.')

    for stub in column_stubs:
        if stub.null_value is None:
            raise RuntimeError(
                f'{template}: column {stub.name!r} declares no null value. Add '
                f'NULL_CONSTANT; the pipeline writes one whenever the column has '
                f'nothing to report.')
        if (stub.valid_minimum is not None
                and stub.valid_minimum == stub.valid_maximum):
            raise RuntimeError(
                f'{template}: column {stub.name!r} declares an empty valid range '
                f'(VALID_MINIMUM == VALID_MAXIMUM == {stub.valid_minimum}), which '
                f'would null every value. Omit both to skip the range check.')

    return ResolvedColumn(key=key, mask=mask,
                          link_fn=link_fn or '', link_id=link_id or '',
                          stubs=tuple(column_stubs))


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

    Parses the host's summary template: a leading run of plain ``COLUMN``
    objects must match the table kind's fixed prefix columns, and the rest of
    the table is a sequence of computation groups, each one
    ``COLUMN_DEFINITION`` followed by its ``COLUMN_STUB`` objects. Template
    order is output order.

    The result is cached per (template directory, qualifier).

    Parameters:
        template_dir: The host's ``templates/`` directory.
        qualifier: ``'sky'``, ``'sun'``, ``'ring'``, or ``'body'``.

    Returns:
        The resolved schema.

    Raises:
        RuntimeError: If the prefix columns do not match or carry a spec
            keyword, a plain COLUMN appears among the groups, a stub has no
            definition, a definition has no stubs or more than two, a
            definition omits BACKPLANE_KEY or malforms a spec keyword, only
            one of LINK_FN and LINK_ID is given, LINK_FN is unknown, a group's
            stubs derive different conversions, a column omits its null value
            or FORMAT, declares an unrecognized unit or an empty valid range,
            or an overflow format does not fill its field.
    """
    template_dir = FCPath(template_dir)
    cache_key = (template_dir.as_posix(), qualifier)
    if cache_key in _schema_cache:
        return _schema_cache[cache_key]

    template_path = template_dir / template_name_for(template_dir, qualifier)
    # PdsTemplate expands $INCLUDE into .content at construction; the column
    # definitions live in the shared fragments, so this expansion is required.
    template = PdsTemplate(template_path, crlf=True,
                           includes=[defs.GLOBAL_TEMPLATE_PATH, template_dir])
    try:
        blocks = column_grammar.tokenize(template.content)
    except ValueError as error:
        raise RuntimeError(f'{template_path}: {error}') from None

    # Consume the fixed prefix run of plain COLUMN objects.
    expected = PREFIX_NAMES[qualifier]
    index = 0
    prefix_stubs: list[ColumnStub] = []
    while index < len(blocks) and blocks[index].kind == 'COLUMN':
        block = blocks[index]
        name = _block_name(block, template_path)
        for keyword in PRIVATE_KEYWORDS:
            if column_grammar.keyword_value(block.body, keyword) is not None:
                raise RuntimeError(
                    f'{template_path}: prefix column {name!r} carries the spec '
                    f'keyword {keyword}; prefix columns are not computed')
        view = _BlockView(block.body, None, name, template_path)
        prefix_stubs.append(_make_stub(view, name, template_path))
        index += 1

    found = tuple(stub.name for stub in prefix_stubs)
    if found != expected:
        raise RuntimeError(
            f'{template_path}: the {qualifier} table must begin with the prefix '
            f'columns {expected}, but the template begins with {found}')

    # The rest of the table is definition/stub groups.
    columns: list[ResolvedColumn] = []
    while index < len(blocks):
        block = blocks[index]
        if block.kind == 'COLUMN':
            raise RuntimeError(
                f'{template_path}: plain COLUMN {_block_name(block, template_path)!r} '
                f'appears among the geometry columns; a computed column is a '
                f'COLUMN_DEFINITION followed by its COLUMN_STUB objects')
        if block.kind == 'COLUMN_STUB':
            raise RuntimeError(
                f'{template_path}: stub {_block_name(block, template_path)!r} has no '
                f'preceding COLUMN_DEFINITION')

        stubs: list[column_grammar.Block] = []
        index += 1
        while index < len(blocks) and blocks[index].kind == 'COLUMN_STUB':
            stubs.append(blocks[index])
            index += 1
        columns.append(_resolve_group(block, stubs, template_path))

    schema = TableSchema(prefix_stubs=tuple(prefix_stubs), columns=tuple(columns))
    _schema_cache[cache_key] = schema
    return schema
