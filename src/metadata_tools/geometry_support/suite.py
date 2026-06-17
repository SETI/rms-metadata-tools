################################################################################
# geometry_support/suite.py - The Suite class (a volume's geometry tables).
################################################################################
import fnmatch
import traceback
from pathlib import Path
from typing import Any, cast

import geometry_config as config
from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.util as util
from metadata_tools.geometry_support import formats
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
                       selection: str = '', glob: str | None = None,
                       index_glob: str | None = None, first: int | None = None,
                       sampling: int = 8) -> None:
        """Construct a geometry Suite object.

        Parameters:
            input_dir: Directory containing the volume.
            output_dir: Directory in which to write the geometry files.
            template_path: Path to the host template.
            metadata_dir: Directory containing the metadata files.
            selection: A string containing "S" to generate summary files and "D"
                to generate detailed files.
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
        self.input_dir = FCPath(input_dir)
        self.output_dir = FCPath(output_dir)
        self.metadata_dir = FCPath(metadata_dir)
        self.template_path = FCPath(template_path)
        self.glob = glob
        self.index_glob = index_glob
        self.first = first
        self.sampling = sampling

        # Determine processing levels
        self.levels: list[str] = []
        for sel in selection:
            if sel == 'S':
                self.levels += ['summary']
            if sel == 'D':
                self.levels += ['detailed']

        # Check for supplemental index
        index_filenames = list(self.metadata_dir.glob(cast(str, self.index_glob)))
        if len(index_filenames) == 0:
            return
        if len(index_filenames) > 1:
            raise RuntimeError('Multiple index files found in %s.' % self.input_dir)

        index_filename = index_filenames[0]
        ext = index_filename.suffix
        self.volume_id = config.get_volume_id(self.input_dir)
        supplemental_index_name = util.get_index_name(self.input_dir,
                                                      self.volume_id, 'supplemental')
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
            logger.error(traceback.format_exc())

        # Initialize data tables
        for level in self.levels:
            self.add_tables(output_dir, level)

        # Initialize meshgrids
        self.meshgrids = config.meshgrids(sampling)

    #===========================================================================
    @staticmethod
    def get_override(record: Record, qualifier: str,
                     name: str | None = None) -> list[dict[str, Any]]:
        """Build a dictionary of column overrides.

        Parameters:
            record: Any Record.
            qualifier: 'sky', 'sun', 'ring', or 'body'.
            name: Name identifying a specific column description.

        Returns:
            Dicts containing override names and values for each column.
        """

        column_descs = record.dicts[qualifier]
        if name:
            column_descs = column_descs[name]

        overrides: list[dict[str, Any]] = []
        for column_desc in column_descs:
            # Get format for this column
            event_key = column_desc[0]
            if len(column_desc) > 2:
                fmt = formats.ALT_FORMAT_DICT[(event_key[0], column_desc[2])]
            else:
                fmt = formats.FORMAT_DICT[event_key[0]]

            # Save label overrides for this column
            (_,_,_,_,_, null_value, valid_minimum, valid_maximum, _, _) = fmt
            override = {'NULL_VALUE':    null_value,
                        'VALID_MINIMUM': valid_minimum,
                        'VALID_MAXIMUM': valid_maximum,
                       }
            overrides.append(override)

        return overrides

    #===========================================================================
    @staticmethod
    def get_overrides(record: Record) -> dict[str, list[dict[str, Any]]]:
        """Build a dictionary of column overrides keyed by qualifier.

        Parameters:
            record: Any Record.

        Returns:
            Dicts containing override names and values for each column, keyed by
            qualifier.
        """
        overrides: dict[str, list[dict[str, Any]]] = {}

        overrides['sky'] = Suite.get_override(record, 'sky')
#        overrides['sun'] = Suite.get_override(record, 'sun')
        overrides['ring'] = Suite.get_override(record, 'ring', name=record.primary)
        overrides['body'] = Suite.get_override(record, 'body', name=record.primary)

        return overrides

    #===========================================================================
    def add_tables(self, output_dir: str | Path | FCPath, level: str) -> None:
        """Add a set of tables.

        Parameters:
            output_dir: Directory in which to write the geometry files.
            level: 'summary' or 'detailed'.
        """
        self.tables: list[InventoryTable | SkyTable | RingTable | BodyTable] = [
            InventoryTable(output_dir, self.template_path, volume_id=self.volume_id),
            SkyTable(output_dir, self.template_path, volume_id=self.volume_id, level=level),
#            SunTable(output_dir, self.template_path, volume_id=self.volume_id, level=level),
            RingTable(output_dir, self.template_path, volume_id=self.volume_id, level=level),
            BodyTable(output_dir, self.template_path, volume_id=self.volume_id, level=level)
            ]

    #===========================================================================
    def make_records(self, index: int) -> list[Record]:
        """Add a record for each processing level.

        Parameters:
            index: Row index.

        Returns:
            One record for each processing level.
        """
        records: list[Record] = []
        for level in self.levels:
            records.append(
                Record(self.observations[index],
                       self.volume_id,
                       self.meshgrids,
                       self.sampling,
                       level))
        return records

    #===========================================================================
    def add(self, records: list[Record]) -> None:
        """Add a row to all tables.

        Parameters:
            records: Records describing the rows to add, one for each processing
                level.
        """
        for table in self.tables:
            for record in records:
                if (record.level == table.level) | (table.level is None):
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
                records = self.make_records(i)
#                   # Build overrides dict
#                   if count == 0:
#                       overrides = Suite.get_overrides(records[0])
                # Update the tables
                self.add(records)
                count += 1

        # Run post-processor
#        self.post()

        # Write tables and make labels
        self.write(labels_only=labels_only)

        # Clean up
        config.cleanup()
        logger.close()
