"""The geometry column computation catalog.

A :class:`ColumnSpec` says how to *compute* one geometry column: which backplane
key to evaluate, which bodies mask it, and how to convert the result. It does
not say whether the column exists, where it appears, how wide it is, or what
its null and valid range are -- the host's label template says all of that, and
:mod:`metadata_tools.geometry_support.label_schema` reads it back.

The link between the two is the column NAME. A spec carries one NAME per value
it produces (two for a min/max pair, one for a single-valued column), and
:func:`name_map` inverts the catalog so a template NAME resolves to the spec and
slot that computes it. A catalog entry no template mentions is simply unused,
which is how a host trims columns it does not want.

This mirrors the index pipeline, where ``key__<NAME>`` functions supply values
for the columns its template declares.
"""
from dataclasses import dataclass
from typing import Any

# A format tuple is (flag, overflow_format, link_id, link), holding the little
# about a column that a PDS3 label cannot express. Everything a label *can*
# express -- the column set and its order, each column's NAME, its width and
# print format (from FORMAT), its null value, and its valid range -- lives in
# the host's template and is read back by
# metadata_tools.geometry_support.label_schema.
#
#   flag = "DEG"  = convert values from radians to degrees;
#        = "360"  = convert to degrees; report cyclic coverage in the range (0,360);
#        = "-180" = convert to degrees; report cyclic coverage in the range (-180,180);
#        = "ISO"  = format TAI seconds as an ISO date-time string;
#        = "KM"   = tabulate values in km, with no unit conversion applied;
#        = ""     = do not modify value.
#
#   overflow_format is the print format substituted when a value overflows its
#   field width, or None when the column cannot overflow.
#
#   link_id is a positive integer id that can be used to link multiple columns
#   via the specified link function. All columns with the same link function and
#   link id are linked together.
#
# To add a geometry column, see "Adding a geometry column" in the developer
# guide; the label template is the starting point, not this file.

FormatTuple = tuple[str, str | None, int, str]


#===============================================================================
@dataclass(frozen=True)
class ColumnSpec:
    """How to compute one geometry column.

    Attributes:
        names: The template NAME of each value this column produces, in slot
            order. Length matches the number of values: two for a min/max pair,
            one for a single-valued column.
        key: The backplane key passed to ``Backplane.evaluate()``. May still
            contain the ``defs.BODYX`` placeholder, substituted per body when
            the row is built.
        mask: ``(masker, shadower, face)``. The masker and shadower strings
            concatenate ``"P"`` (planet), ``"R"`` (rings), and ``"M"`` (blocker
            body); the face is ``"D"``, ``"N"``, or ``""``.
        format: ``(flag, overflow_format, link_id, link)`` -- the conversion,
            overflow, and link metadata a PDS3 label cannot express. See the
            comment at the top of this module.
    """

    names: tuple[str, ...]
    key: tuple[Any, ...]
    mask: tuple[str, str, str]
    format: FormatTuple

    @property
    def number_of_values(self) -> int:
        """The number of values this column produces."""
        return len(self.names)


#===============================================================================
def _format(flag: str, overflow: str | None, link_id: int, link: str) -> FormatTuple:
    """Assemble a format tuple, validating the link fields.

    Parameters:
        flag: Unit-conversion flag; see the module comment.
        overflow: Print format used when a value overflows its field, or None.
        link_id: Link group id, or 0 for an unlinked column.
        link: Link function name, or '' for an unlinked column.

    Returns:
        The format tuple.

    Raises:
        ValueError: If only one of link_id and link is given.
    """
    if bool(link_id) != bool(link):
        raise ValueError(
            f'link_id={link_id!r} and link={link!r} must be given together or not at all')
    return (flag, overflow, link_id, link)


#===============================================================================
def minmax(base: str, key: tuple[Any, ...], mask: tuple[str, str, str],
           flag: str = '', overflow: str | None = None,
           link_id: int = 0, link: str = '') -> ColumnSpec:
    """Build a spec for the usual ``MINIMUM_<base>`` / ``MAXIMUM_<base>`` pair.

    Parameters:
        base: The NAME stem shared by the two columns.
        key: The backplane key.
        mask: ``(masker, shadower, face)``.
        flag: Unit-conversion flag; see the module comment.
        overflow: Print format used when a value overflows its field.
        link_id: Link group id, for columns that go null together.
        link: Link function name.

    Returns:
        The column specification.
    """
    return ColumnSpec(('MINIMUM_' + base, 'MAXIMUM_' + base), key, mask,
                      _format(flag, overflow, link_id, link))


#===============================================================================
def pair(low: str, high: str, key: tuple[Any, ...], mask: tuple[str, str, str],
         flag: str = '', overflow: str | None = None,
         link_id: int = 0, link: str = '') -> ColumnSpec:
    """Build a spec for a two-value column whose NAMEs are not MINIMUM/MAXIMUM.

    Used for the ring resolutions, which are named ``FINEST_``/``COARSEST_``.
    Stripping a prefix would be ambiguous -- body's
    ``MINIMUM_FINEST_SURFACE_RESOLUTION`` is an ordinary min/max pair whose stem
    happens to start with ``FINEST_`` -- so both NAMEs are given explicitly.

    Parameters:
        low: The NAME of the first (minimum) value.
        high: The NAME of the second (maximum) value.
        key: The backplane key.
        mask: ``(masker, shadower, face)``.
        flag: Unit-conversion flag; see the module comment.
        overflow: Print format used when a value overflows its field.
        link_id: Link group id, for columns that go null together.
        link: Link function name.

    Returns:
        The column specification.
    """
    return ColumnSpec((low, high), key, mask, _format(flag, overflow, link_id, link))


#===============================================================================
def single(name: str, key: tuple[Any, ...], mask: tuple[str, str, str],
           flag: str = '', overflow: str | None = None,
           link_id: int = 0, link: str = '') -> ColumnSpec:
    """Build a spec for a single-valued column.

    Parameters:
        name: The column's template NAME.
        key: The backplane key.
        mask: ``(masker, shadower, face)``.
        flag: Unit-conversion flag; see the module comment.
        overflow: Print format used when a value overflows its field.
        link_id: Link group id, for columns that go null together.
        link: Link function name.

    Returns:
        The column specification.
    """
    return ColumnSpec((name,), key, mask, _format(flag, overflow, link_id, link))


#===============================================================================
def get_catalog(qualifier: str) -> tuple[ColumnSpec, ...]:
    """Return the catalog for one table kind.

    Parameters:
        qualifier: ``'sky'``, ``'sun'``, ``'ring'``, or ``'body'``.

    Returns:
        Every column specification defined for that kind, in catalog order.
        Template order, not this order, determines output order.

    Raises:
        KeyError: If the qualifier has no catalog.
    """
    # Imported here rather than at module scope: the catalog modules import the
    # helpers defined above, so a top-level import would be circular.
    from metadata_tools.columns.body import BODY_CATALOG
    from metadata_tools.columns.ring import RING_CATALOG
    from metadata_tools.columns.sky import SKY_CATALOG
    from metadata_tools.columns.sun import SUN_CATALOG

    catalogs: dict[str, tuple[ColumnSpec, ...]] = {
        'body': BODY_CATALOG,
        'ring': RING_CATALOG,
        'sky': SKY_CATALOG,
        'sun': SUN_CATALOG,
    }
    return catalogs[qualifier]


#===============================================================================
def name_map(qualifier: str) -> dict[str, tuple[ColumnSpec, int]]:
    """Invert a catalog so a template NAME resolves to its spec and value slot.

    Parameters:
        qualifier: ``'sky'``, ``'sun'``, ``'ring'``, or ``'body'``.

    Returns:
        A mapping from column NAME to ``(spec, slot)``, where slot indexes into
        the spec's values.

    Raises:
        ValueError: If two specs in the catalog claim the same NAME, which would
            make the template's reference to it ambiguous.
    """
    mapping: dict[str, tuple[ColumnSpec, int]] = {}
    for spec in get_catalog(qualifier):
        for slot, name in enumerate(spec.names):
            if name in mapping:
                raise ValueError(
                    f'duplicate column NAME {name!r} in the {qualifier} catalog: '
                    f'claimed by both {mapping[name][0].key} and {spec.key}')
            mapping[name] = (spec, slot)
    return mapping
