=====================
Index table subsystem
=====================

Overview
========

The index subsystem builds supplemental index tables: extra columns appended to
a project's corrected index file, one row per data product. It is implemented in
:mod:`metadata_tools.index_support` and produces output through
:func:`~metadata_tools.index_support.process_index`.

Entry point and walk
====================

:func:`~metadata_tools.index_support.process_index` parses the template name to
find the host and index type, parses the command line through
:func:`~metadata_tools.index_support.get_args` (built on
:func:`~metadata_tools.common.get_common_args`), and calls the private
``_create_index`` helper. That helper walks the volume tree, and for each
directory that matches the volume glob it constructs an
:class:`~metadata_tools.index_support.IndexTable` and calls
:meth:`~metadata_tools.index_support.IndexTable.create`. A ``__skip`` directory
anywhere in the path is ignored, which keeps test fixtures out of a run.

IndexTable
==========

:class:`~metadata_tools.index_support.IndexTable` describes one volume's index.
Construction reads the column definitions ("stubs") from the supplemental label
template: each stub records the column ``NAME``, Fortran ``FORMAT``, ``ITEMS``
count, and null constant. The file list comes from the primary (corrected) index
file when one exists, or from a recursive scan of the volume's ``.LBL`` files
when the table being built *is* the primary index.

:meth:`~metadata_tools.index_support.IndexTable.create` iterates the files and
calls :meth:`~metadata_tools.index_support.IndexTable.add`, which reads each PDS3
label into a dictionary and formats one value per column. Columns that never
receive a non-null value across the whole run are collected in ``unused`` and
logged as a warning.

The value-resolution contract
=============================

For each column, ``_index_one_value`` decides where the value comes from, in
this order:

#. A built-in key function named ``key__<name>`` defined in
   :mod:`metadata_tools.index_support` (for example
   :func:`~metadata_tools.index_support.key__volume_id` and
   :func:`~metadata_tools.index_support.key__file_specification_name`).
#. A host key function ``key__<name>`` defined in the host's ``index_config``
   module.
#. Otherwise, the value is taken straight from the PDS3 label dictionary.

A key function receives the label path and the label dictionary and returns the
value to write. Returning ``None`` inserts the column's null constant; if no null
constant is defined for that column, a ``ValueError`` is raised. The lookup is
explicit (not exception-driven), so an error raised *inside* a key function
propagates rather than being swallowed. This is the primary extension point for
index tables; see :doc:`dev_guide_extending`.

Formatting
==========

Values are written with Fortran format codes through the ``fortranformat``
library. ``_format_column`` handles multi-item columns (the ``ITEMS`` count),
cleans up strings (collapsing whitespace and stripping embedded quotes), and
falls back to an overflow representation when a value does not fit. Character
columns are quoted.

API reference
=============

See :doc:`api/index_support`.
