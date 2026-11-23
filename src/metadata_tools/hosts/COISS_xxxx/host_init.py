"""Initialize the Cassini ISS host module.

Importing this module for its side effects initializes the ``rms-host-cassini``
ISS host. It is imported by this host's ``geometry_config`` module, which the
config registry loads lazily on the first ``get_geometry_config()`` call. The body
registry (``metadata_tools.bodies``) is built lazily on its own first call and
needs no import here.
"""
import cspyce
import spicedb
from filecache import FCPath
from host_cassini.oops import CassiniISS

CassiniISS.initialize()


#===============================================================================
# TEMPORARY WORKAROUND: remove once SETI/rms-host-cassini#42 is released.
#
# The host loads its C kernels from the SPICE database, which lists none of the
# cruise C kernels in Cassini/CK-cruise/; without them, about 6,300 COISS_1xxx
# images have no pointing and are dropped from the geometry tables. Furnish them
# here instead. They go in after the gapfill C kernels that initialize() loads,
# so they take precedence over those, and before the reconstructed C kernels,
# which the host furnishes lazily as observations need them and which therefore
# take precedence over these where both cover a time.
#
# To remove: once a release of rms-host-cassini loads the cruise C kernels,
# require it in pyproject.toml, delete this block and its test
# (tests/hosts/COISS_xxxx/test_spice.py, test_cruise_kernels_give_pointing), and
# the note in CLAUDE.md.
#===============================================================================
CRUISE_CK_DIR = 'Cassini/CK-cruise'


def _furnish_cruise_cks() -> list[str]:
    """Furnish every C kernel in the cruise directory of the SPICE tree.

    Returns:
        The local paths of the furnished kernels, in load order.

    Raises:
        FileNotFoundError: If the directory holds no C kernels, since every cruise
            image would then silently lose its pointing.
    """
    root = FCPath(spicedb.get_spice_path())
    paths = [str(path.retrieve()) for path in sorted(root.glob(CRUISE_CK_DIR + '/*.bc'))]
    if not paths:
        raise FileNotFoundError(f'no C kernels in {root / CRUISE_CK_DIR}')
    for path in paths:
        cspyce.furnsh(path)
    return paths


CRUISE_CKS = _furnish_cruise_cks()
