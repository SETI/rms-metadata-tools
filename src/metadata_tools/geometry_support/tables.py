################################################################################
# geometry_support/tables.py - Geometry table classes.
################################################################################
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
    """Class describing a sun geometry table."""

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

        Parameters:
            record: Record describing the row to add.
        """
        self.rows += record.add(cast(str, self.qualifier))


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

        Parameters:
            record: Record describing the row to add.
        """

        # Add record
        if record.primary:
            if record.rings_present:
                self.rows += record.add(cast(str, self.qualifier), name=record.primary)

#        # Add other rings
#        for name in record.bodies
#           if record.rings_present:
#               self.rows += record.add(self.qualifier, name=name,
#                                       target=name+'-ring', no_mask=True


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
        """Add a Body row.

        Parameters:
            record: Record describing the row to add.
        """
        for name in record.bodies:
            self.rows += record.add(cast(str, self.qualifier), name=name, target=name)
