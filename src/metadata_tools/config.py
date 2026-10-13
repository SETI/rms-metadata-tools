################################################################################
# config.py - Runtime registry for the active host's config modules.
################################################################################
"""Runtime registry for the active host's config modules (see issue #112).

Generic engine modules (``index_support``, ``geometry_support``,
``cumulative_support``) call :func:`get_host_config`, :func:`get_index_config`,
and :func:`get_geometry_config` instead of doing a top-level ``import
host_config``. Entry points call :func:`set_host` once, before touching any
engine code, to populate the registry for the host being processed.
"""
import importlib
import types
from pathlib import Path
from typing import Any, cast

from filecache import FCPath

import metadata_tools.util as util

_host_id: str | None = None
_host_config: types.ModuleType | None = None
_index_config: types.ModuleType | None = None
_geometry_config: types.ModuleType | None = None


#===============================================================================
def set_host(host_id: str) -> None:
    """Import and register the config modules for *host_id*.

    Eagerly resolves ``metadata_tools.hosts.<host_id>.{host_config,index_config}``
    as package-qualified imports, so no ``sys.path`` manipulation is required.
    ``geometry_config`` (and the ``host_init`` side-effect it carries - SPICE
    initialization and backplane column registration) is loaded lazily on the
    first :func:`get_geometry_config` call, so index and cumulative workers
    never pay the SPICE startup cost.

    Parameters:
        host_id: Host directory name, e.g. 'GO_0xxx'.
    """
    global _host_id, _host_config, _index_config, _geometry_config
    base = f'metadata_tools.hosts.{host_id}'
    # Import first, then commit: a failed import must not leave the registry
    # with the new host ID paired with the previous host's config modules.
    host_config = importlib.import_module(f'{base}.host_config')
    index_config = importlib.import_module(f'{base}.index_config')
    _host_id = host_id
    _host_config = host_config
    _index_config = index_config
    _geometry_config = None  # loaded lazily in get_geometry_config()

#===============================================================================
def set_current(*,
                host_id: str,
                host_config: types.ModuleType,
                index_config: types.ModuleType,
                geometry_config: types.ModuleType) -> None:
    """Install already-resolved config modules as the active host.

    Lower-level setter used by :func:`set_host` and by tests to install
    lightweight fake modules without importing SPICE-dependent real host
    modules.

    Parameters:
        host_id: Host directory name, e.g. 'GO_0xxx'.
        host_config: The host's host_config module (or a stand-in).
        index_config: The host's index_config module (or a stand-in).
        geometry_config: The host's geometry_config module (or a stand-in).
    """
    global _host_id, _host_config, _index_config, _geometry_config
    _host_id = host_id
    _host_config = host_config
    _index_config = index_config
    _geometry_config = geometry_config

#===============================================================================
def current_host_id() -> str:
    """The currently registered host id.

    Returns:
        The host id passed to the most recent :func:`set_host` or
        :func:`set_current` call.

    Raises:
        RuntimeError: If no host has been registered yet.
    """
    if _host_id is None:
        raise RuntimeError(
            'metadata_tools.config.set_host() has not been called')
    return _host_id

#===============================================================================
def get_host_config() -> types.ModuleType:
    """The currently registered host's host_config module.

    Returns:
        The host_config module registered via :func:`set_host` or
        :func:`set_current`.

    Raises:
        RuntimeError: If no host has been registered yet.
    """
    if _host_config is None:
        raise RuntimeError(
            'metadata_tools.config.set_host() has not been called')
    return _host_config

#===============================================================================
def get_index_config() -> types.ModuleType:
    """The currently registered host's index_config module.

    Returns:
        The index_config module registered via :func:`set_host` or
        :func:`set_current`.

    Raises:
        RuntimeError: If no host has been registered yet.
    """
    if _index_config is None:
        raise RuntimeError(
            'metadata_tools.config.set_host() has not been called')
    return _index_config

#===============================================================================
def get_geometry_config() -> types.ModuleType:
    """The currently registered host's geometry_config module.

    The module is imported on the first call (lazy loading), which triggers
    that host's ``host_init`` side-effect (SPICE initialization and backplane
    column registration). Subsequent calls return the cached module.

    Returns:
        The geometry_config module for the active host.

    Raises:
        RuntimeError: If :func:`set_host` or :func:`set_current` has not been
            called yet.
    """
    global _geometry_config
    if _geometry_config is None:
        if _host_id is None:
            raise RuntimeError(
                'metadata_tools.config.set_host() has not been called')
        _geometry_config = importlib.import_module(
            f'metadata_tools.hosts.{_host_id}.geometry_config')
    return _geometry_config

################################################################################
# Host hooks with engine defaults
#
#  A host defines one of these only where it must differ from the default.
################################################################################

#===============================================================================
def get_volume_id(path: str | Path | FCPath) -> str:
    """Determine the volume ID from a path into a volume tree.

    Parameters:
        path: Path to a volume, or to anything inside one.

    Returns:
        The result of the host's ``host_config.get_volume_id`` if it defines
        one; otherwise that of :func:`metadata_tools.util.get_volume_id`.
    """
    hook = getattr(get_host_config(), 'get_volume_id', None)
    if hook is not None:
        return cast(str, hook(path))
    return util.get_volume_id(path)

#===============================================================================
def get_exclude() -> list[str] | None:
    """The volumes the host excludes from processing.

    Returns:
        The host's ``host_config.exclude`` if it defines one; otherwise None,
        for which each stage excludes the cumulative volume of the tree it is
        processing.
    """
    return cast('list[str] | None', getattr(get_host_config(), 'exclude', None))

#===============================================================================
def get_index_glob() -> str | None:
    """The glob matching a volume's index label in its metadata directory.

    Returns:
        The host's ``geometry_config.index_glob`` if it defines one; otherwise
        None, for which the label is named for the volume,
        ``<volume_id>_index.lbl``.
    """
    return cast('str | None', getattr(get_geometry_config(), 'index_glob', None))

#===============================================================================
def get_target_name(observation_dict: dict[str, Any]) -> str:
    """Determine the target of an observation.

    Parameters:
        observation_dict: The observation's dictionary of index values.

    Returns:
        The result of the host's ``geometry_config.target_name`` if it defines
        one; otherwise the observation's TARGET_NAME.
    """
    hook = getattr(get_geometry_config(), 'target_name', None)
    if hook is not None:
        return str(hook(observation_dict))
    return str(observation_dict['TARGET_NAME'])

#===============================================================================
def cleanup() -> None:
    """Clean up after a volume's geometry tables and labels are written.

    Calls the host's ``geometry_config.cleanup`` if it defines one.
    """
    hook = getattr(get_geometry_config(), 'cleanup', None)
    if hook is not None:
        hook()

#===============================================================================
def get_expand() -> float:
    """The border the host allows around a field of view, for pointing uncertainty.

    Returns:
        The host's ``geometry_config.EXPAND``, in radians, if it defines one;
        otherwise 0.
    """
    return float(getattr(get_geometry_config(), 'EXPAND', 0.))

#===============================================================================
def get_meshgrids(sampling: float) -> dict[Any, Any]:
    """The meshgrids a volume's observations choose from.

    Parameters:
        sampling: Pixel sampling density.

    Returns:
        The result of the host's ``geometry_config.meshgrids`` if it defines
        one; otherwise an empty dictionary, which the engine fills with a
        meshgrid for each FOV it meets.
    """
    hook = getattr(get_geometry_config(), 'meshgrids', None)
    if hook is not None:
        return cast('dict[Any, Any]', hook(sampling))
    return {}
