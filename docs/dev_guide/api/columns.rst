============================
Geometry column definitions
============================

The ``columns`` subpackage holds the geometry column *computation catalogs*:
how to compute each column. Which columns a host actually writes is decided by
its label templates and resolved by
:mod:`metadata_tools.geometry_support.label_schema`.

``metadata_tools.columns``
==========================

.. automodule:: metadata_tools.columns

The package ``__init__`` re-exports the names below from the submodules; each is
documented on its submodule's page.

``metadata_tools.columns.catalog``
==================================

.. automodule:: metadata_tools.columns.catalog
   :members:
   :show-inheritance:

..
   :undoc-members: is omitted here: the dataclass fields are already described
   in each class's Attributes section, and autodoc would emit them a second
   time as undocumented members.

``metadata_tools.columns.formats``
==================================

.. automodule:: metadata_tools.columns.formats
   :members:
   :undoc-members:
   :show-inheritance:

``metadata_tools.columns.body``
===============================

.. automodule:: metadata_tools.columns.body
   :members:
   :undoc-members:
   :show-inheritance:

``metadata_tools.columns.ring``
===============================

.. automodule:: metadata_tools.columns.ring
   :members:
   :undoc-members:
   :show-inheritance:

``metadata_tools.columns.sky``
==============================

.. automodule:: metadata_tools.columns.sky
   :members:
   :undoc-members:
   :show-inheritance:

``metadata_tools.columns.sun``
==============================

.. automodule:: metadata_tools.columns.sun
   :members:
   :undoc-members:
   :show-inheritance:
