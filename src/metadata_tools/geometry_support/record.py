################################################################################
# geometry_support/record.py - The Record class (one geometry table row).
################################################################################
"""Geometry record class for accumulating per-row column values."""
from collections.abc import Sequence
from dataclasses import replace as dataclass_replace
from typing import TYPE_CHECKING, Any

import oops

import metadata_tools.bodies as bodies_mod
import metadata_tools.defs as defs
import metadata_tools.util as util
from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support import bodies_select, formats, meshgrids, prep
from metadata_tools.geometry_support.link_fns import LinkedField, LinkFunction

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
    - ``backplane``: the ``oops`` Backplane sampling the observation's whole
      field of view.
    - ``inventory``: the bodies in the field of view; empty, with
      ``pointing_available`` set to False, when SPICE pointing is unavailable.
    - ``bodies``: the bodies to tabulate, and ``blocker``: the target, when it is
      in the field of view and can block or shadow the others, else None.
    - ``boxes``: the bounding box of each tabulated body, and of the primary's
      ring system, that is in the field of view; see :meth:`backplane_for`.
      Empty when body-specific meshgrids are disabled.

    Each table then calls :meth:`add` with its resolved columns to produce its
    rows for this observation.
    """

    #===========================================================================
    def __init__(self, observation: Any, volume_id: str, meshgrids: dict[str, Any],
                 sampling: int, body_samples: int = 16) -> None:
        """Construct a geometry record.

        Parameters:
            observation: OOPS Observation object.
            volume_id: Volume ID.
            meshgrids: All meshgrids associated with this host.
            sampling: Pixel sampling density.
            body_samples: Minimum number of samples across the bounding box of
                a body or ring system; 0 to sample every table on the meshgrid
                of the whole field of view instead.
        """
        self.observation = observation
        config = get_geometry_config()

        # Determine primary, if any
        sclk = str(observation.dict["SPACECRAFT_CLOCK_START_COUNT"])
        self.primary, self.secondaries, self.selections, self.additions = \
            bodies_select.get_primary(self, formats.get_mission_table(), sclk)
        self.sampling = sampling
        self.body_samples = body_samples
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
        self.meshgrid = self._meshgrid(observation, meshgrids)
        self.backplane = oops.backplane.Backplane(observation, self.meshgrid)
        self._backplanes: dict[str, tuple[Any, int]] = {}

        # Get inventory for this record
        self.inventory = bodies_select.inventory(self, bodies_mod.get_bodies_registry())

        # Select bodies for this record
        self.bodies = bodies_select.select_bodies(self, bodies_mod.get_bodies_registry())

        # Define a blocker body, if any
        if self.target in self.bodies:
            blocker = bodies_select.inventory(self, [self.target])
            if blocker:
                self.blocker = blocker[0]

        # Locate each body, and the primary's ring system, in the image
        self.boxes: dict[str, tuple[Any, tuple[float, float]]] = {}
        if body_samples > 0:
            located = list(self.bodies)
            if self.rings_present and oops.Body.exists(self.ring_system):
                located.append(self.ring_system)
            self.boxes = bodies_select.bounding_boxes(self, located)

    #===========================================================================
    @property
    def ring_system(self) -> str:
        """The name of the body bounding the primary's ring system."""
        return self.primary + '_RING_SYSTEM'

    #===========================================================================
    def backplane_for(self, body: str | None) -> tuple[Any, int]:
        """Return the backplane on which to tabulate one body.

        A body in the field of view is sampled on a meshgrid of its own,
        spanning its bounding box, so that it is resolved however small it
        appears. Each such backplane is built once and then reused.

        Parameters:
            body: Name of the body or ring system, or None for a quantity that
                belongs to no body.

        Returns:
            The backplane and its pixel sampling density. These are the
            backplane sampling the whole field of view, and the record's
            sampling, unless the body has a bounding box of its own.
        """
        if body is None or body not in self.boxes:
            return self.backplane, self.sampling

        if body not in self._backplanes:
            center_uv, size_uv = self.boxes[body]
            grid = meshgrids.box_meshgrid(self.meshgrid, center_uv, size_uv,
                                          self.sampling, self.body_samples)
            if grid is None:
                self._backplanes[body] = (self.backplane, self.sampling)
            else:
                meshgrid, sampling = grid
                self._backplanes[body] = (
                    oops.backplane.Backplane(self.observation, meshgrid), sampling)

        return self._backplanes[body]

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
            key = util.replace(column.key, defs.BODYX, name)
            out.append(dataclass_replace(column, key=key))
        return out

    #===========================================================================
    def postprocess(self, columns: list[str],
                    resolved: Sequence['ResolvedColumn']) -> list[str]:
        """Process the completed record.

        Calls each link group's link function (see
        :mod:`metadata_tools.geometry_support.link_fns`) on the group's values.

        Parameters:
            columns: One str for each column, prefix columns included.
            resolved: The table's resolved columns, describing the data columns
                at the end of *columns*.

        Returns:
            The processed columns.

        Raises:
            RuntimeError: If a linked column's field count disagrees with its
                number of values.
        """
        ndata = len(resolved)
        if not ndata:
            return columns
        data_columns = columns[-ndata:]

        # Gather each link group's fields, keyed by the group's LINK_ID.
        #
        # data_columns holds one entry per column, not per value: prep_row
        # appends a single string per column, and a min/max column's two values
        # are already comma-joined inside it. Each is split into one field per
        # value, so a link function sees every value under its own NAME.
        groups: dict[str, tuple[LinkFunction, list[tuple[int, list[LinkedField]]]]] = {}
        for position, column in enumerate(resolved):
            if column.link_fn is None:
                continue
            texts = data_columns[position].split(',')
            if len(texts) != len(column.stubs):
                raise RuntimeError(
                    f'linked column {column.stubs[0].name!r} holds {len(texts)} '
                    f'comma-separated fields for {len(column.stubs)} values')
            fields = [LinkedField(stub, text)
                      for stub, text in zip(column.stubs, texts, strict=True)]
            groups.setdefault(column.link_id, (column.link_fn, []))[1].append(
                (position, fields))

        # Call each group's link function, then write its fields back.
        for link_fn, members in groups.values():
            link_fn({field.stub.name: field
                     for _position, fields in members for field in fields})
            for position, fields in members:
                data_columns[position] = ','.join(field.text for field in fields)

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
                  grid: str | None = None,
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
            grid: Optionally, the body or ring system whose bounding box is to
                be sampled; by default the whole field of view is.
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
        backplane, sampling = self.backplane_for(grid)
        rows = prep.prep_row(self, self.prefixes, backplane, self.blocker,
                             columns,
                             primary=self.primary, target=target,
                             sampling=sampling,
                             ignore_shadows=ignore_shadows,
                             allow_zero_rows=allow_zero_rows,
                             no_mask=no_mask,
                             no_body=no_body)

        # Postprocess the rows and append to the output
        lines: list[str] = []
        for row in rows:
            lines.append(','.join(self.postprocess(row, columns)))

        return lines
