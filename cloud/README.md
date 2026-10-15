# cloud/

This directory holds the Google Cloud configurations for the `*-cloud` commands
(`metadata-index-cloud`, `metadata-geometry-cloud`, and
`metadata-cumulative-cloud`), one subdirectory per host:

```text
cloud/
  GO_0xxx/
    gcp_<stage>_config.yml        # small single-instance setup, for testing
    gcp_<stage>_prod_config.yml   # production fleet for the whole collection
  COISS_xxxx/
    ...
```

Each file is a `cloud_tasks` configuration: the GCP project and zone, the
machine families, the fleet size, the CPUs and memory per task, the runtime
limit, the boot disk, the retry policy, and a price cap. The comments in each
production file explain how its values were chosen.

## Why this is not under `src/metadata_tools/hosts/`

Everything else a host needs lives in `src/metadata_tools/hosts/<HOST>/`.
These files do not, because they are deployment settings rather than part of
the program:

- **They describe one operator's account.** `project_id: rms-metadata`, the
  region, the fleet sizes, and the price caps belong to the RMS Node's GCP
  project, not to the host. They have no business in a public package that
  anyone can install.
- **They change on their own schedule.** A fleet is retuned when prices,
  quotas, or machine families change, without any change to the code and
  without a new release.
- **Runs leave artifacts beside them.** Task lists and job databases are
  written where runs are launched. Keeping them in a tree of their own, with
  their patterns in `.gitignore`, keeps them out of the package source; some
  were once committed by accident.

Only packages under `src/` are installed (see `[tool.setuptools.packages.find]`
in `pyproject.toml`), so nothing here ships in the wheel.

The cost is that a host's files are split between two trees: adding a host
means adding `src/metadata_tools/hosts/<HOST>/` and, to run it on GCP,
`cloud/<HOST>/`.

## How the commands find these files

- With no `--config`, a `*-cloud` command uses
  `cloud/<HOST>/gcp_<stage>_config.yml` if it exists. That works only in a
  source checkout; from a pip install, pass `--config` explicitly.
- A bare filename given to `--config` or `--task-file` is looked for in
  `cloud/<HOST>/`; use a `./` prefix or an absolute path for a file elsewhere.
- Select a production setup by name, e.g.
  `--config gcp_geometry_prod_config.yml`.

The instance startup script is not stored here. It is generated at dispatch
time from `src/metadata_tools/cli/gcp_common_startup.sh`, which does ship with
the package, so that dispatch works from a pip install.

## Hosts

- `GO_0xxx`: index, geometry, and cumulative stages.
- `COISS_xxxx`: geometry and cumulative stages only, since the Cassini ISS host
  has no index stage. Its output tree needs a directory, holding at least one
  file, for each volume before the geometry stage runs.

See the "Distributed (cloud) runs" chapter of the user guide for the commands and their
options.
