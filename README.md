# rms-metadata-tools

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
[![DOI](https://zenodo.org/badge/rms-metadata-tools.svg)](https://zenodo.org/badge/latestdoi/rms-metadata-tools)
<!-- start-after-point -->

## Introduction

`rms-metadata-tools` (the importable package `metadata_tools`) generates PDS3
**index**, **geometry**, and **cumulative** metadata tables, and their PDS3
labels, for planetary science data collections. Each row of a table holds the
metadata for a single data product, such as one image.

The Planetary Data System (PDS) distributes data as collections of volumes.
Alongside the data, each collection ships flat ASCII metadata tables that
summarize every product: observation times, instrument settings, and the
geometry of what was observed. These tables feed the
[OPUS](https://opus.pds-rings.seti.org) search service and are downloaded
directly by PDS users. Producing them by hand is tedious and error-prone;
`rms-metadata-tools` generates them, and their validated labels, for a whole
volume tree from a small per-collection configuration.

`rms-metadata-tools` is a product of the
[PDS Ring-Moon Systems Node](https://pds-rings.seti.org) at the SETI Institute.

## Features

- **Three table kinds.** Generates supplemental **index** tables (extra columns
  from PDS3 labels), **geometry** tables (body, ring, sky, and Sun quantities
  computed from SPICE through `oops`), and **cumulative** tables that span a
  whole collection.
- **PDS3 labels included.** Writes a validated `.lbl` label for every table from
  reusable templates.
- **Engine plus per-host configuration.** A host-agnostic engine does the work;
  each collection plugs in through a small configuration package, so adding a new
  collection means writing config, not engine code.
- **Local or cloud.** Run on one machine, or distribute per-volume work across
  Google Cloud with the included `rms-cloud-tasks` workers.
- **Local and remote storage.** Reads and writes through `rms-filecache`, so
  local paths and `gs://` / `s3://` URIs are interchangeable.

## Installation

`rms-metadata-tools` requires **Python 3.11 or later** and is tested on Python
3.11, 3.12, and 3.13. Generating geometry tables additionally requires the SPICE
kernels for your collection, installed where `oops` can find them.

Install from PyPI:

```sh
pip install rms-metadata-tools
```

To work from a checkout (recommended when adding or modifying a host
configuration, since the runnable host scripts live in the source tree):

```sh
git clone https://github.com/SETI/rms-metadata-tools.git
cd rms-metadata-tools
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

The optional extras are `dev` (linting, type-checking, tests, docs), `docs`
(Sphinx), and `cloud` (the GCP workers).

## Quick Start

Each supported collection ("host") has its own runnable programs in its
directory under `src/metadata_tools/hosts/<HOST>/`. They import their
configuration as top-level modules, so run them from inside the host directory.
The three stages, for the Galileo SSI host, are:

```sh
cd src/metadata_tools/hosts/GO_0xxx

# 1. Supplemental index tables (extra columns from the PDS3 labels)
python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
    "$RMS_METADATA_TEST/GO_0xxx/"

# 2. Geometry tables (body/ring/sky/Sun quantities from SPICE)
python GO_0xxx_geometry.py "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/"

# 3. Cumulative tables across the whole collection
python GO_0xxx_cumulative.py "$RMS_METADATA_TEST/GO_0xxx/GO_0999/"
```

Path arguments are expanded for environment variables. Restrict a run to one
volume with `-vv GO_0017`, or to a few images with `--first 5`. See the
[user guide](https://rms-metadata-tools.readthedocs.io/en/latest/user_guide/user_guide.html)
for the full list of programs and options.

## Documentation

Full documentation is hosted on
[ReadTheDocs](https://rms-metadata-tools.readthedocs.io). It includes a user
guide (installation, configuration, and a reference for every command-line
program) and a developer guide (architecture, per-subsystem internals, how to
add a new collection or geometry column, and the API reference).

To build the documentation locally:

```sh
scripts/read-docs.sh
```

## Contributing

Information on contributing to this package can be found in the
[Contributing Guide](https://github.com/SETI/rms-metadata-tools/blob/main/CONTRIBUTING.md).

## Links

- [Documentation](https://rms-metadata-tools.readthedocs.io)
- [Repository](https://github.com/SETI/rms-metadata-tools)
- [Issue tracker](https://github.com/SETI/rms-metadata-tools/issues)
- [PyPI](https://pypi.org/project/rms-metadata-tools)

## Licensing

This code is licensed under the
[Apache License v2.0](https://github.com/SETI/rms-metadata-tools/blob/main/LICENSE).
