[![GitHub release; latest by date](https://img.shields.io/github/v/release/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/releases)
[![Test Status](https://img.shields.io/github/actions/workflow/status/SETI/rms-metadata-tools/run-tests.yml?branch=main)](https://github.com/SETI/rms-metadata-tools/actions)
[![Documentation Status](https://readthedocs.org/projects/rms-metadata-tools/badge/?version=latest)](https://rms-metadata-tools.readthedocs.io/en/latest/?badge=latest)
[![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-metadata-tools/main?logo=codecov)](https://codecov.io/gh/SETI/rms-metadata-tools)
<br />
[![PyPI - Version](https://img.shields.io/pypi/v/rms-metadata-tools)](https://pypi.org/project/rms-metadata-tools)
[![PyPI - Format](https://img.shields.io/pypi/format/rms-metadata-tools)](https://pypi.org/project/rms-metadata-tools)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rms-metadata-tools)](https://pypi.org/project/rms-metadata-tools)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rms-metadata-tools)](https://pypi.org/project/rms-metadata-tools)
<br />
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/SETI/rms-metadata-tools/latest)](https://github.com/SETI/rms-metadata-tools/commits/main/)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/commits/main/)
[![GitHub last commit](https://img.shields.io/github/last-commit/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/commits/main/)
<br />
[![Number of GitHub open issues](https://img.shields.io/github/issues-raw/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/issues)
[![Number of GitHub closed issues](https://img.shields.io/github/issues-closed-raw/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/issues)
[![Number of GitHub open pull requests](https://img.shields.io/github/issues-pr-raw/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/pulls)
[![Number of GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/pulls)
<br />
![GitHub License](https://img.shields.io/github/license/SETI/rms-metadata-tools)
[![Number of GitHub stars](https://img.shields.io/github/stars/SETI/rms-metadata-tools)](https://github.com/SETI/rms-metadata-tools/stargazers)
![GitHub forks](https://img.shields.io/github/forks/SETI/rms-metadata-tools)

# Introduction

`metadata-tools` is a Python module that generates index and geometry metadata tables
and their corresponding PDS3 labels. Each line of the table contains metadata for a single
data file (e.g. image).

Index files contain descriptive information about the data product, like observation
times, exposures, instrument modes and settings, etc. Index file entries are taken from
the label for the data product by default, but may instead be derived from label
quantities by defining the appropriate configuration function in the host_config.py
for the specific host.

Raw index files are provided by each project, with varying levels of compliance. The
project-supplied index files are modified to produce the corrected index  files that
can be used with the host from_index() method. The ``metadata-tools`` package is intended
to produce supplemental index files, which add columns to the corrected index file.
Supplemental index files are identical in structure to index files, so this package can
generate any kind of index file. Supplemental index files can be provded as arguments to
from_index() to create a merged dictionary.

Supplemental index files are used as input to OPUS, and are available via viewmaster to be
downloaded by PDS users.

Geometry files tabulate the values of geometrc quantites for each data file, which are
derived from SPICE using the information in the index file or from the PDS3 label using
OOPS.  The purpose of the geometry files is to provide input to OPUS.

# Generating New Matadata Tables

The procedure for generating metadata tables is as follows:

 1. Create a directory for the new host collection under the hosts/ subdirectory, e.g.,
    GO_0xxx, COISS_xxxx, etc.

 2. Copy the python files from an existing host directory and rename them according to
    the new collection.  You should have these files:

    __init.py__
    host_init.py
    host_config.py
    index_config.py
    geometry_config.py
    <collection>_index.py
    <collection>_geometry.py
    <collection>_cumulative.py

 3. Create a templates/ subdirectory and copy the label templates from an existing host,
    and rename accordingly, yielding:

    templates/<collection>_supplmental_index.lbl
    templates/<collection>_body_summary.lbl
    templates/<collection>_ring_summary.lbl
    templates/host_defs.lbl

 4. Edit the config modules as needed.

 5. Edit the supplemental and summary templates and generate the tables using
    <collection>_index.py and <collection>_geometry.py according to the instructions in
    those files.

 6. Generate the cumulative tables using <collection>_cumulative.py according to the
    instructions in that file.

# Unit Tests

Copy and edit the unit tests from the tests/ directory of an existing host. Run all tests
from the rms-metadata-tools/ directory using:

    python -m unitest

        or

    python -m pytest
