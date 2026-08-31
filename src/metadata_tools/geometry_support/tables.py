################################################################################
# geometry_support/tables.py - Geometry table classes.
################################################################################
"""Geometry table classes: InventoryTable, SkyTable, SunTable, RingTable, BodyTable."""
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from filecache import FCPath

import metadata_tools.common as com

if TYPE_CHECKING:
    from metadata_tools.geometry_support.record import Record


################################################################################
# InventoryTable class
################################################################################
class InventoryTable(com.Table):
    """Class describing an inventory geometry table."""

    #===========================================================================
    def __init__(self, output_dir: str | Path | FCPath | None = None,
                 template_path: str | Path | FCPath | None = None,
                 **kwargs: Any) -> None:
        """Constructor for an InventoryTable object.

        Parameters:
            output_dir: Directory in which to write the geometry files.
            template_path: Path to the host template.
            kwargs: Additional keyword arguments forwarded to the base class.
        """
        super().__init__(output_dir=output_dir, template_path=template_path,
                         qualifier='inventory',
                         suffix="_inventory.csv",
                         use_global_template=True,
                         level=None, **kwargs)

    #===========================================================================
    def add(self, record: 'Record') -> None:
        """Add an Inventory row.

        Parameters:
            record: Record describing the row to add.
        """
        line = ",".join(record.prefixes) + ',"' + ",".join(record.inventory) + '"'
        self.rows += [line]


################################################################################
# SkyTable class
################################################################################
class SkyTable(com.Table):
    """Class describing a sky geometry table."""

    #===========================================================================
    def __init__(self, output_dir: str | Path | FCPath | None = None,
                 template_path: str | Path | FCPath | None = None,
                 **kwargs: Any) -> None:
        """Constructor for a SkyTable object.

        Parameters:
            output_dir: Directory in which to write the geometry files.
            template_path: Path to the host template.
            kwargs: Additional keyword arguments forwarded to the base class.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='sky',
                         **kwargs)

    #===============================================================================
    def add(self, record: 'Record') -> None:
        """Add a Sky row.

        Parameters:
            record: Record describing the row to add.
        """
        self.rows += record.add(cast(str, self.qualifier), no_body=True)


################################################################################
# SunTable class
################################################################################
class SunTable(com.Table):
    """Class describing a sun geometry table. Not wired into the pipeline.

    The Sun is a body like any other, so a sun table is structured like the body
    table (its rows carry the same SYSTEM_NAME/BODY_NAME prefixes) with a single
    fixed target. It differs only in that the Sun is itself the illumination
    source, so its column set (``SUN_SUMMARY_COLUMNS`` in ``columns/sun.py``)
    omits every illumination-based quantity (phase, incidence, sub-solar, ...).

    This table is intentionally NOT wired into the pipeline, because ``oops``
    cannot evaluate any Sun-surface backplane. ``oops`` models the Sun
    as the sole illumination source and prepends ``'SUN<'`` to every surface
    event key; when the target surface is itself the Sun,
    ``Backplane.standardize_event_key`` collapses the duplicate
    ``('SUN<', 'SUN')`` to the illegal length-1 key ``('SUN<',)`` and raises
    ``ValueError: illegal surface event key``. Every ``SUN_COLUMNS`` key hits
    this, so no sun row can be generated. Resolving it requires additional
    backplane support that ``oops`` does not provide (e.g. a self-illuminated /
    observer-only surface event key), not a change here.

    Enablement recipe, should ``oops`` gain support for Sun-surface geometry:
      1. In ``suite.Suite.add_tables``, add ``SunTable`` at the ``'summary'``
         level (the Sun has no per-body tiling, so no detailed variant), and add
         it to the ``self.tables`` type annotation.
      2. In ``suite.Suite.get_overrides``, add
         ``overrides['sun'] = Suite.get_override(record, 'sun')``.
      3. In ``cumulative_support.create_cumulative_indexes``, add
         ``geom.SunTable(level='summary')`` to the table list.
      4. The label templates already exist and are validated:
         ``hosts/GO_0xxx/templates/GO_0xxx_sun_summary.lbl`` and the shared
         ``templates/sun_summary_columns.lbl`` (guarded by
         ``tests/test_geometry_sun_label.py``).
    """

    #===========================================================================
    def __init__(self, output_dir: str | Path | FCPath | None = None,
                 template_path: str | Path | FCPath | None = None,
                 **kwargs: Any) -> None:
        """Constructor for a SunTable object.

        Parameters:
            output_dir: Directory in which to write the geometry files.
            template_path: Path to the host template.
            kwargs: Additional keyword arguments forwarded to the base class.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='sun',
                         **kwargs)

    #===========================================================================
    def add(self, record: 'Record') -> None:
        """Add a Sun row.

        The Sun is treated as a body, so its row uses the same body-name
        prefixing as the body table, with a single fixed target. See the class
        docstring: this cannot run unless ``oops`` can evaluate Sun-surface
        backplanes.

        Parameters:
            record: Record describing the row to add.
        """
        self.rows += record.add(cast(str, self.qualifier), target='SUN')


################################################################################
# RingTable class
################################################################################
class RingTable(com.Table):
    """Class describing a ring geometry table."""

    #===========================================================================
    def __init__(self, output_dir: str | Path | FCPath | None = None,
                 template_path: str | Path | FCPath | None = None,
                 **kwargs: Any) -> None:
        """Constructor for a RingTable object.

        Parameters:
            output_dir: Directory in which to write the geometry files.
            template_path: Path to the host template.
            kwargs: Additional keyword arguments forwarded to the base class.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='ring',
                         **kwargs)

    #===========================================================================
    def add(self, record: 'Record') -> None:
        """Add a Ring row.

        A row is added only when the record has a primary body and that primary
        has rings.

        Parameters:
            record: Record describing the row to add.
        """

        # Add record
        if record.primary:
            if record.rings_present:
                self.rows += record.add(cast(str, self.qualifier), name=record.primary)


################################################################################
# BodyTable class
################################################################################
class BodyTable(com.Table):
    """Class describing a body geometry table."""

    #===========================================================================
    def __init__(self, output_dir: str | Path | FCPath | None = None,
                 template_path: str | Path | FCPath | None = None,
                 **kwargs: Any) -> None:
        """Constructor for a BodyTable object.

        Parameters:
            output_dir: Directory in which to write the geometry files.
            template_path: Path to the host template.
            kwargs: Additional keyword arguments forwarded to the base class.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='body',
                         **kwargs)

    #===========================================================================
    def add(self, record: 'Record') -> None:
        """Add a row for each body selected in the record.

        Parameters:
            record: Record describing the rows to add; one row is added per
                entry in record.bodies.
        """
        for name in record.bodies:
            self.rows += record.add(cast(str, self.qualifier), name=name, target=name)
