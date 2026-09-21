################################################################################
# geometry_support/label_schema.py - Read a geometry table's schema from its label
# template.
################################################################################
"""Resolve a geometry table's column schema from its PDS3 label template.

The template is the source of truth for which geometry columns a host writes,
in what order, and with what width, print format, null value, and valid range.
This module parses it and joins each COLUMN's NAME against the computation
catalog in :mod:`metadata_tools.columns`, producing the
:class:`TableSchema` that :mod:`~metadata_tools.geometry_support.prep` walks
when it builds a row.

This mirrors :class:`metadata_tools.index_support.table.IndexTable`, which
already derives its columns from its own template.

Validation is deliberately loud and happens once, when the table is
constructed, rather than silently producing a misaligned row per observation.
A template that names an unknown column, splits a min/max pair, or omits a
null value fails the run immediately.
"""
import re
from dataclasses import dataclass
from typing import Any

from filecache import FCPath
from pdstemplate import PdsTemplate
from pdstemplate.pds3table import Pds3Table

import metadata_tools.defs as defs
from metadata_tools.columns.catalog import ColumnSpec, name_map

# The prefix columns each table kind writes ahead of its geometry columns, in
# order. These come from Record.prefixes and prep.append_body_prefix, not from
# the catalog, so they are matched by name and skipped.
PREFIX_NAMES: dict[str, tuple[str, ...]] = {
    'sky':  ('VOLUME_ID', 'FILE_SPECIFICATION_NAME'),
    'ring': ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME'),
    'body': ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME', 'BODY_NAME'),
    'sun':  ('VOLUME_ID', 'FILE_SPECIFICATION_NAME', 'SYSTEM_NAME', 'BODY_NAME'),
}

# Null keywords in priority order, matching IndexTable._get_null_value.
_NULL_KEYWORDS = ('NULL_CONSTANT', 'UNKNOWN_CONSTANT', 'INVALID_CONSTANT',
                  'MISSING_CONSTANT', 'NOT_APPLICABLE_CONSTANT')

# "F12.3" -> ("F", "12", "3");  "A23" -> ("A", "23", None)
_FORMAT_RE = re.compile(r'^([FAEI])(\d+)(?:\.(\d+))?$')


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
    """

    name: str
    width: int
    print_format: str
    null_value: float | str | None
    valid_minimum: float | None
    valid_maximum: float | None


#===============================================================================
@dataclass(frozen=True)
class ResolvedColumn:
    """One template column joined to the catalog entry that computes it.

    Attributes:
        spec: The catalog entry supplying the backplane key, mask, and
            conversion flag.
        stubs: The label metadata for each of the spec's values, in slot order.
    """

    spec: ColumnSpec
    stubs: tuple[ColumnStub, ...]


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
def _read_stubs(template_path: FCPath) -> list[ColumnStub]:
    """Parse every COLUMN object out of a label template, in order.

    Parameters:
        template_path: Path to the host's summary label template.

    Returns:
        One stub per COLUMN object, in template order.

    Raises:
        RuntimeError: If a column's FORMAT is missing or unsupported.
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

    stubs: list[ColumnStub] = []
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

        width, print_format = _parse_format(str(name), pds3.old_lookup('FORMAT', colnum),
                                            template_path)
        stubs.append(ColumnStub(name=str(name).strip().strip('"'),
                                width=width,
                                print_format=print_format,
                                null_value=null,
                                valid_minimum=pds3.old_lookup('VALID_MINIMUM', colnum),
                                valid_maximum=pds3.old_lookup('VALID_MAXIMUM', colnum)))
        colnum += 1

    return stubs


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
    joins each remaining COLUMN's NAME against the qualifier's computation
    catalog. Template order becomes output order. A catalog entry the template
    never names is simply unused, which is how a host drops a column.

    The result is cached per (template directory, qualifier).

    Parameters:
        template_dir: The host's ``templates/`` directory.
        qualifier: ``'sky'``, ``'sun'``, ``'ring'``, or ``'body'``.

    Returns:
        The resolved schema.

    Raises:
        RuntimeError: If the prefix columns do not match, a NAME is absent from
            the catalog, a multi-value column's NAMEs are not adjacent and in
            slot order, a column declares no null value, or a column declares an
            empty valid range.
    """
    template_dir = FCPath(template_dir)
    cache_key = (template_dir.as_posix(), qualifier)
    if cache_key in _schema_cache:
        return _schema_cache[cache_key]

    template_path = template_dir / template_name_for(template_dir, qualifier)
    stubs = _read_stubs(template_path)

    # Consume the fixed prefix run.
    expected = PREFIX_NAMES[qualifier]
    found = tuple(stub.name for stub in stubs[:len(expected)])
    if found != expected:
        raise RuntimeError(
            f'{template_path}: the {qualifier} table must begin with the prefix columns '
            f'{expected}, but the template begins with {found}')
    prefix_stubs = tuple(stubs[:len(expected)])
    data_stubs = stubs[len(expected):]

    mapping = name_map(qualifier)
    for stub in data_stubs:
        if stub.name in expected:
            raise RuntimeError(
                f'{template_path}: prefix column {stub.name!r} reappears among the '
                f'geometry columns')

    columns: list[ResolvedColumn] = []
    index = 0
    while index < len(data_stubs):
        stub = data_stubs[index]
        try:
            spec, slot = mapping[stub.name]
        except KeyError:
            raise RuntimeError(
                f'{template_path}: column {stub.name!r} is not in the {qualifier} catalog, '
                f'so nothing knows how to compute it. Add a ColumnSpec to '
                f'metadata_tools.columns.{qualifier}, or remove the column from the '
                f'template.') from None

        if slot != 0:
            raise RuntimeError(
                f'{template_path}: column {stub.name!r} is value {slot + 1} of '
                f'{spec.names}, but appears before {spec.names[0]!r}. A multi-value '
                f'column\'s parts must appear together, in order.')

        group = data_stubs[index:index + spec.number_of_values]
        actual = tuple(s.name for s in group)
        if actual != spec.names:
            raise RuntimeError(
                f'{template_path}: column {spec.names[0]!r} must be followed immediately '
                f'by {spec.names[1:]}, but the template has {actual[1:]}. A multi-value '
                f'column\'s parts must appear together, in order.')

        for member in group:
            if member.null_value is None:
                raise RuntimeError(
                    f'{template_path}: column {member.name!r} declares no null value. '
                    f'Add NULL_CONSTANT; the pipeline writes one whenever the column has '
                    f'nothing to report.')
            if (member.valid_minimum is not None
                    and member.valid_minimum == member.valid_maximum):
                raise RuntimeError(
                    f'{template_path}: column {member.name!r} declares an empty valid '
                    f'range (VALID_MINIMUM == VALID_MAXIMUM == {member.valid_minimum}), '
                    f'which would null every value. Omit both to skip the range check.')

        columns.append(ResolvedColumn(spec=spec, stubs=tuple(group)))
        index += spec.number_of_values

    schema = TableSchema(prefix_stubs=prefix_stubs, columns=tuple(columns))
    _schema_cache[cache_key] = schema
    return schema
