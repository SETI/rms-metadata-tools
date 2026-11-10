################################################################################
# geometry_support/record.py - The Record class (one geometry table row).
################################################################################
"""Geometry record class for accumulating per-row column values."""
from collections.abc import Callable, Sequence
from dataclasses import replace as dataclass_replace
from typing import TYPE_CHECKING, Any

import oops

import metadata_tools.bodies as bodies_mod
import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support import bodies_select, formats, prep

if TYPE_CHECKING:
    from metadata_tools.geometry_support.label_schema import ResolvedColumn


################################################################################
# Record class
################################################################################
class Record:
    """The geometry of one observation, from which each table builds its rows.

    Construction does all of the SPICE work for the observation, after which these
    attributes are always set:

    - ``primary``, ``secondaries``, ``selections``, ``additions``: the bodies the
      host's mission table assigns to the observation's spacecraft clock
      (``primary`` is empty when there is none).
    - ``rings_present``: True only when there is a primary with a ring frame.
    - ``target``: the target name, from the host's ``target_name`` hook.
    - ``prefixes``: the quoted volume ID and file specification that begin every row.
    - ``backplane``: the ``oops`` Backplane for the observation.
    - ``inventory``: the bodies in the field of view; empty, with
      ``pointing_available`` set to False, when SPICE pointing is unavailable.
    - ``bodies``: the bodies to tabulate, and ``blocker``: the target, when it is
      in the field of view and can block or shadow the others, else None.

    Each table then calls :meth:`add` with its resolved columns to produce its
    rows for this observation.
    """

    #===========================================================================
    def __init__(self, observation: Any, volume_id: str, meshgrids: dict[str, Any],
                 sampling: int) -> None:
        """Construct a geometry record.

        Parameters:
            observation: OOPS Observation object.
            volume_id: Volume ID.
            meshgrids: All meshgrids associated with this host.
            sampling: Pixel sampling density.
        """
        self.observation = observation
        config = get_geometry_config()

        # Determine primary, if any
        sclk = str(observation.dict["SPACECRAFT_CLOCK_START_COUNT"])
        self.primary, self.secondaries, self.selections, self.additions = \
            bodies_select.get_primary(self, formats.get_mission_table(), sclk)
        self.sampling = sampling
        self.pointing_available = True

        # Set up planet-based geometry
        self.bodies: list[str] = []
        self.blocker: str | None = None

        self.rings_present = False
        if self.primary:
            registry = bodies_mod.get_bodies_registry()
            self.rings_present = registry[self.primary].ring_frame is not None

        # Determine target
        self.target = str(config.target_name(observation.dict))

        # Create the record prefix
        filespec = observation.dict["FILE_SPECIFICATION_NAME"]
        self.prefixes = ['"' + volume_id + '"',
                         '"%-32s"' % filespec.replace(".IMG", ".LBL")]

        # Create the backplanes
        meshgrid = self._meshgrid(observation, meshgrids)
        self.backplane = oops.backplane.Backplane(observation, meshgrid)

        # Get inventory for this record
        self.inventory = bodies_select.inventory(self, bodies_mod.get_bodies_registry())

        # Select bodies for this record
        self.bodies = bodies_select.select_bodies(self, bodies_mod.get_bodies_registry())

        # Define a blocker body, if any
        if self.target in self.bodies:
            blocker = bodies_select.inventory(self, [self.target])
            if blocker:
                self.blocker = blocker[0]

    #===========================================================================
    @staticmethod
    def substitute(columns: Sequence['ResolvedColumn'],
                   name: str) -> 'list[ResolvedColumn]':
        """Resolve the BODYX placeholder in every column's backplane key.

        Parameters:
            columns: The table's resolved columns.
            name: The body name to substitute.

        Returns:
            The columns, with each backplane key bound to *name*.
        """
        out: list[ResolvedColumn] = []
        for column in columns:
            # The key is wrapped in a list because util.replace resolves an
            # embedded dictionary reference -- the ring system radius lookup --
            # only inside a nested list or tuple leaf, never at the top level.
            key = util.replace([column.key], defs.BODYX, name)[0]
            out.append(dataclass_replace(column, key=key))
        return out

    #===========================================================================
    def postprocess(self, columns: list[str],
                    resolved: Sequence['ResolvedColumn']) -> list[str]:
        """Process the completed record.

        Parameters:
            columns: One str for each column, prefix columns included.
            resolved: The table's resolved columns, describing the data columns
                at the end of *columns*.

        Returns:
            The processed columns.
        """

        def link_null(indices: list[int], null_value: Any,
                      data_columns: list[str]) -> list[str]:
            """Null every column in a link group if any one of them is null.

            Parameters:
                indices: Positions of the linked columns within data_columns.
                null_value: The null value shared by the group.
                data_columns: Column values.

            Returns:
                The updated data columns.
            """
            for i in indices:
                val = data_columns[i]
                if float(val) == null_value:
                    for j in indices:
                        data_columns[j] = val
                    break

            return data_columns

        _link_dispatch: dict[str, Callable[[list[int], Any, list[str]], list[str]]] = {
            'null': link_null,
        }

        # Group the data-column positions by link function and link id.
        #
        # These are positions in the *row*, which holds one entry per column,
        # not per value: prep_row appends a single string per column, and a
        # min/max column's two values are already comma-joined inside it. So a
        # column advances the position by one however many values it carries.
        groups: dict[tuple[str, str], tuple[list[int], Any]] = {}
        for position, column in enumerate(resolved):
            if column.link_id:
                indices, _null = groups.setdefault((column.link_fn, column.link_id),
                                                   ([], column.stubs[0].null_value))
                indices.append(position)

        ndata = len(resolved)
        if not ndata:
            return columns
        data_columns = columns[-ndata:]

        # Call link functions
        for (link_fn, _link_id), (indices, null_value) in groups.items():
            data_columns = _link_dispatch[link_fn](indices, null_value, data_columns)

        # Substitute new data columns
        columns[-ndata:] = data_columns

        return columns

    #===============================================================================
    def _meshgrid(self, observation: Any, meshgrids: dict[str, Any]) -> Any:
        """Look up the meshgrid for an observation.

        Parameters:
            observation: OOPS Observation object.
            meshgrids: All meshgrids associated with this host.

        Returns:
            Meshgrid for the given observation.
        """
        return get_geometry_config().meshgrid(meshgrids, observation)

    #===============================================================================
    def add(self, columns: Sequence['ResolvedColumn'], *,
                  name: str | None = None, target: str | None = None,
                  ignore_shadows: bool = False,
                  allow_zero_rows: bool = True, no_mask: bool = False,
                  no_body: bool = False) -> list[str]:
        """Generate the geometry for one row, given a table's resolved columns.

        At most one record is produced per call; if all values are null, a
        record is produced only when allow_zero_rows is False.

        Parameters:
            columns: The table's resolved columns, in template order.
            name: The body to bind the BODYX placeholder to, if the columns
                carry one.
            target: Optionally, the target name to write into the record.
            ignore_shadows: True to ignore any mask constraints applicable to
                shadowing or to the sunlit faces of surfaces.
            allow_zero_rows: True to allow the function to return no rows. If
                False, a row filled with null values will be returned if
                necessary.
            no_mask: True to suppress the use of a mask.
            no_body: True to suppress body prefixes.

        Returns:
            The formatted output rows.
        """
        if name:
            columns = Record.substitute(columns, name)

        # Prepare the rows
        rows = prep.prep_row(self, self.prefixes, self.backplane, self.blocker,
                             columns,
                             primary=self.primary, target=target,
                             ignore_shadows=ignore_shadows,
                             allow_zero_rows=allow_zero_rows,
                             no_mask=no_mask,
                             no_body=no_body)

        # Postprocess the rows and append to the output
        lines: list[str] = []
        for row in rows:
            lines.append(','.join(self.postprocess(row, columns)))

        return lines
