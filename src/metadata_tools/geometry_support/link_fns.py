################################################################################
# geometry_support/link_fns.py - Link functions for linked geometry columns.
################################################################################
"""Link functions: postprocessing applied jointly to a group of linked columns.

A geometry column joins a link group by declaring ``LINK_ID`` in its label
template. Every column in a table sharing one ``LINK_ID`` forms one group, and
the id names the group's link function: ``LINK_ID = "CENTER_COORDINATE"``
calls ``link__center_coordinate`` (``link__`` plus the id lowercased, as a
``key__<NAME>`` function is named in the index pipeline). The
function is looked up here first and then in the active host's
``geometry_config``, the same order the index pipeline uses for its key
functions, and it is resolved when the template is read, so a
missing one fails the run before any row is written.

A link function receives the group as a mapping from each value's column NAME
to its :class:`LinkedField` -- a minimum/maximum column contributes both of its
values -- and edits the fields in place. Each field carries its own label
metadata, so a function never needs the columns to agree on a null value or a
width. Shared behaviour belongs in a generic helper such as
:func:`null_together`, which a group's own function calls; the per-group
function is the place for anything specific to that group.
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support.formatting import format_field

if TYPE_CHECKING:
    from metadata_tools.geometry_support.label_schema import ColumnStub


#===============================================================================
@dataclass
class LinkedField:
    """One formatted value of a linked column, editable in place."""

    stub: 'ColumnStub'
    """The value's label metadata, which gives its NAME, null value, and format."""

    text: str
    """The formatted field, exactly as it will be written to the row."""

    @property
    def is_null(self) -> bool:
        """True if the field holds its own column's null value."""
        null = self.stub.null_value
        if isinstance(null, str):
            return self.text.strip().strip('"').strip() == null
        try:
            return float(self.text) == null
        except ValueError:
            return False

    def set_null(self) -> None:
        """Replace the field with its own column's null value, formatted."""
        self.text = format_field(self.stub, self.stub.null_value)


# A link group: each linked value's column NAME mapped to its field.
LinkGroup = dict[str, LinkedField]

# A link function, which edits a group's fields in place.
LinkFunction = Callable[[LinkGroup], None]


#===============================================================================
# Generic helpers
#===============================================================================
def null_together(group: LinkGroup) -> None:
    """Null every value in the group if any one of them is null.

    Each value is nulled with its own column's null constant and format, so
    the columns need not agree on either.

    Parameters:
        group: The link group.
    """
    if any(field.is_null for field in group.values()):
        for field in group.values():
            field.set_null()


#===============================================================================
# Link functions, one per LINK_ID
#===============================================================================
def link__center_coordinate(group: LinkGroup) -> None:
    """CENTER_COORDINATE: a centre is reported whole or not at all.

    Parameters:
        group: The centre X and Y coordinates.
    """
    null_together(group)


#===============================================================================
# Lookup
#===============================================================================
def function_name(link_id: str) -> str:
    """Return the name of the link function a LINK_ID calls.

    Parameters:
        link_id: The LINK_ID, e.g. ``'CENTER_COORDINATE'``.

    Returns:
        The function name, e.g. ``'link__center_coordinate'``.
    """
    return 'link__' + link_id.lower()


def find_link_function(link_id: str) -> LinkFunction | None:
    """Find the link function a LINK_ID calls.

    A built-in function in this module takes priority over one defined in the
    active host's ``geometry_config``.

    Parameters:
        link_id: The LINK_ID.

    Returns:
        The function, or None if neither place defines it.
    """
    name = function_name(link_id)
    function = globals().get(name)
    if function is None:
        function = getattr(get_geometry_config(), name, None)
    return function if callable(function) else None
