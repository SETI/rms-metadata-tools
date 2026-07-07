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

_host_id: str | None = None
_host_config: types.ModuleType | None = None
_index_config: types.ModuleType | None = None
_geometry_config: types.ModuleType | None = None


#===============================================================================
def set_host(host_id: str) -> None:
    """Import and register the config modules for *host_id*.

    Resolves ``metadata_tools.hosts.<host_id>.{host_config,index_config,
    geometry_config}`` as package-qualified imports, so no ``sys.path``
    manipulation is required. Importing ``geometry_config`` also triggers that
    host's ``host_init`` side-effect import (SPICE initialization and backplane
    column registration).

    Parameters:
        host_id: Host directory name, e.g. 'GO_0xxx'.
    """
    base = f'metadata_tools.hosts.{host_id}'
    set_current(
        host_id=host_id,
        host_config=importlib.import_module(f'{base}.host_config'),
        index_config=importlib.import_module(f'{base}.index_config'),
        geometry_config=importlib.import_module(f'{base}.geometry_config'),
    )

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

    Returns:
        The geometry_config module registered via :func:`set_host` or
        :func:`set_current`.

    Raises:
        RuntimeError: If no host has been registered yet.
    """
    if _geometry_config is None:
        raise RuntimeError(
            'metadata_tools.config.set_host() has not been called')
    return _geometry_config
