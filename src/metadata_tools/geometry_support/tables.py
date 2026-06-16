################################################################################
# geometry_support/tables.py - Geometry table classes.
################################################################################
import metadata_tools.common as com


################################################################################
# InventoryTable class
################################################################################
class InventoryTable(com.Table):
    """Class describing an inventory geometry table."""

    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for an InventoryTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path,
                         qualifier='inventory',
                         suffix="_inventory.csv",
                         use_global_template=True,
                         level=None, **kwargs)

    #===========================================================================
    def add(self, record):
        """Add an Inventory row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        line = ",".join(record.prefixes) + ',"' + ",".join(record.inventory) + '"'
        self.rows += [line]


################################################################################
# SkyTable class
################################################################################
class SkyTable(com.Table):
    """Class describing a sky geometry table."""

    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a SkyTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='sky',
                         **kwargs)

    #===============================================================================
    def add(self, record):
        """Add a Sky row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        self.rows += record.add(self.qualifier, no_body=True)


################################################################################
# SunTable class
################################################################################
class SunTable(com.Table):
    """Class describing a sun geometry table."""

    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a SunTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='sun',
                         **kwargs)

    #===========================================================================
    def add(self, record):
        """Add a Sun row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        self.rows += record.add(self.qualifier)


################################################################################
# RingTable class
################################################################################
class RingTable(com.Table):
    """Class describing a ring geometry table."""

    #===========================================================================
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a RingTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='ring',
                         **kwargs)

    #===========================================================================
    def add(self, record):
        """Add a Ring row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """

        # Add record
        if record.primary:
            if record.rings_present:
                self.rows += record.add(self.qualifier, name=record.primary)

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
    def __init__(self, output_dir=None, template_path=None, **kwargs):
        """Constructor for a BodyTable object.

        Args:
            output_dir (str, Path, or FCPath):
                Directory in which to write the geometry files.
            template_path (str, Path, or FCPath): Path to the host template.
        """
        super().__init__(output_dir=output_dir, template_path=template_path, qualifier='body',
                         **kwargs)

    #===========================================================================
    def add(self, record):
        """Add a Body row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        for name in record.bodies:
            self.rows += record.add(self.qualifier, name=name, target=name)
