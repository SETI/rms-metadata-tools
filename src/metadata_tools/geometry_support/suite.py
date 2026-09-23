################################################################################
# geometry_support/suite.py - The Suite class (a volume's geometry tables).
################################################################################
"""Suite class orchestrating geometry table generation for one volume."""
import fnmatch
from pathlib import Path
from typing import Any, cast

from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.util as util
from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support.record import Record
from metadata_tools.geometry_support.tables import BodyTable, InventoryTable, RingTable, SkyTable


################################################################################
# Suite class
################################################################################
class Suite:
    """Class describing the suite of geometry tables for a single volume.
    """

    #===========================================================================
    def __init__(self, input_dir: str | Path | FCPath, output_dir: str | Path | FCPath,
                       template_path: str | Path | FCPath,
                       metadata_dir: str | Path | FCPath | None = None,
                       glob: str | None = None,
                       index_glob: str | None = None, first: int | None = None,
                       sampling: int = 8) -> None:
        """Construct a geometry Suite object.

        Parameters:
            input_dir: Directory containing the volume.
            output_dir: Directory in which to write the geometry files.
            template_path: Path to the host template.
            metadata_dir: Directory containing the metadata files.
            glob: Glob pattern for data files.
            index_glob: Glob pattern for index files.
            first: If given, at most this many files are processed in each
                volume.
            sampling: Pixel sampling density.

        Raises:
            RuntimeError: If more than one index file is found in the metadata
                directory.
        """
        # Save inputs
        config = get_geometry_config()
        self.input_dir = FCPath(input_dir)
        self.output_dir = FCPath(output_dir)
        self.metadata_dir = FCPath(metadata_dir)
        self.template_path = FCPath(template_path)
        self.glob = glob
        self.index_glob = index_glob
        self.first = first
        self.sampling = sampling

        # Check for supplemental index
        index_filenames = list(self.metadata_dir.glob(cast(str, self.index_glob)))
        if len(index_filenames) == 0:
            return
        if len(index_filenames) > 1:
            raise RuntimeError('Multiple index files found in %s.' % self.input_dir)

        index_filename = index_filenames[0]
        ext = index_filename.suffix
        self.volume_id = config.get_volume_id(self.input_dir)
        supplemental_index_name = util.get_index_name(self.volume_id, 'supplemental')
        supplemental_index_filename = \
            self.input_dir.joinpath(supplemental_index_name+ext)

        # Initialize the logger
        com.init_logger(self.input_dir, 'geometry')
        logger = com.get_logger()

        logger.info('New geometry index for %s.', self.volume_id)

        # Get observations
        self.observations: Any
        try:
            self.observations = config.from_index(index_filename,
                                                  supplemental_index_filename)
        except FileNotFoundError:
            logger.exception('Index file not found for %s', self.volume_id)
            return

        # Initialize data tables
        self.tables: list[InventoryTable | SkyTable | RingTable | BodyTable] = []
        self.add_tables(output_dir)

        # Initialize meshgrids
        self.meshgrids = config.meshgrids(sampling)

    #===========================================================================
    def add_tables(self, output_dir: str | Path | FCPath) -> None:
        """Create the volume's tables and append them to ``self.tables``.

        Parameters:
            output_dir: Directory in which to write the geometry files.
        """
        # A SunTable would be inserted here; it is not wired in. See
        # tables.SunTable for the blocker and enablement recipe.
        # level='summary' names the output file and its template
        # (<volume>_<qualifier>_summary.tab). The inventory table sets its own
        # level and suffix.
        self.tables += [
            InventoryTable(output_dir, self.template_path, volume_id=self.volume_id),
            SkyTable(output_dir, self.template_path, volume_id=self.volume_id,
                     level='summary'),
            RingTable(output_dir, self.template_path, volume_id=self.volume_id,
                      level='summary'),
            BodyTable(output_dir, self.template_path, volume_id=self.volume_id,
                      level='summary')
            ]

    #===========================================================================
    def make_record(self, index: int) -> Record:
        """Create the record for one observation.

        Parameters:
            index: Row index.

        Returns:
            The record describing that observation.
        """
        return Record(self.observations[index],
                      self.volume_id,
                      self.meshgrids,
                      self.sampling)

    #===========================================================================
    def add(self, record: Record) -> None:
        """Add a row to all tables.

        Parameters:
            record: Record describing the row to add.
        """
        for table in self.tables:
            table.add(record)

    #===========================================================================
    def write(self, labels_only: bool = False) -> None:
        """Write all tables and their labels.

        Parameters:
            labels_only: If True, labels are generated for any existing geometry
                tables.
        """
        for table in self.tables:
            table.write(labels_only=labels_only)

    #===========================================================================
    def create(self, labels_only: bool = False, pattern: str | None = None) -> None:
        """Process the volume and write a suite of geometry files.

        Parameters:
            labels_only: If True, labels are generated for any existing geometry
                tables.
            pattern: Glob pattern for sub-selecting files to process.
        """
        logger = com.get_logger()

        if not hasattr(self, 'observations'):
            return

        # Loop through the observations...
        nobs = len(self.observations)
        count = 0
        if not labels_only:
            for i in range(nobs):
                name = self.observations[i].basename

                # Make any sub selection
                if pattern and fnmatch.filter([self.observations[i].filespec], pattern) == []:
                    logger.warning("Skipping %s; pattern mismatch.", name)
                    continue

                # Match the glob pattern
                match = fnmatch.filter([name], self.glob)
                if match == []:
                    logger.warning("Skipping %s; glob mismatch.", name)
                    continue
                file = match[0]

                # Abort if count exceeds a specified limit
                if self.first and count >= self.first:
                    continue

                # Print a log of progress
                logger.info("%s  %s %4d/%4d", self.volume_id, file, i+1, nobs)

                # Construct the record for this observation
                record = self.make_record(i)
                # Update the tables
                self.add(record)
                count += 1

        # Write tables and make labels
        self.write(labels_only=labels_only)

        # Clean up
        get_geometry_config().cleanup()
        logger.close()
