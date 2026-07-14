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

    Eagerly resolves ``metadata_tools.hosts.<host_id>.{host_config,index_config}``
    as package-qualified imports, so no ``sys.path`` manipulation is required.
    ``geometry_config`` (and the ``host_init`` side-effect it carries — SPICE
    initialization and backplane column registration) is loaded lazily on the
    first :func:`get_geometry_config` call, so index and cumulative workers
    never pay the SPICE startup cost.

    Parameters:
        host_id: Host directory name, e.g. 'GO_0xxx'.
    """
    global _host_id, _host_config, _index_config, _geometry_config
    base = f'metadata_tools.hosts.{host_id}'
    _host_id = host_id
    _host_config = importlib.import_module(f'{base}.host_config')
    _index_config = importlib.import_module(f'{base}.index_config')
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
    column registration).  Subsequent calls return the cached module.

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
