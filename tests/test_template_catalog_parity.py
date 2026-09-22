################################################################################
# tests/test_template_catalog_parity.py: TEMPORARY template-vs-catalog parity.
################################################################################
"""Prove the annotated templates carry exactly what the catalogs carried.

The computation spec now lives in private keywords inside the label templates;
the Python catalogs in ``metadata_tools.columns`` are the outgoing copy. This
module pins the two against each other, exhaustively, for the one commit in
which both exist. It is deleted together with the catalogs.
"""
from pathlib import Path
from typing import Any

import pytest
from filecache import FCPath

import metadata_tools
from metadata_tools.columns.catalog import get_catalog, name_map
from metadata_tools.geometry_support.label_schema import resolve_schema

TEMPLATE_DIR = FCPath(
    Path(metadata_tools.__file__).parent / 'hosts' / 'GO_0xxx' / 'templates')

QUALIFIERS = ('body', 'ring', 'sky', 'sun')


@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_template_specs_match_the_catalog(qualifier: str) -> None:
    """Every resolved column carries its catalog entry's spec, field by field."""
    mapping = name_map(qualifier)
    schema = resolve_schema(TEMPLATE_DIR, qualifier)

    for column in schema.columns:
        spec, slot = mapping[column.stubs[0].name]
        assert slot == 0
        assert tuple(stub.name for stub in column.stubs) == spec.names
        assert column.key == spec.key
        assert column.mask == spec.mask
        for stub in column.stubs:
            assert stub.overflow_format == spec.overflow_format, stub.name
        # The id spelling changed (int -> named token), so compare the
        # grouping, not the value: linked exactly when the catalog links.
        assert bool(column.link_id) == bool(spec.link_id), column.stubs[0].name
        if spec.link_id:
            assert column.link_fn == spec.link


@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_every_catalog_entry_is_in_the_template(qualifier: str) -> None:
    """The templates reference the whole catalog: nothing was dropped."""
    schema = resolve_schema(TEMPLATE_DIR, qualifier)
    assert len(schema.columns) == len(get_catalog(qualifier))


@pytest.mark.parametrize('qualifier', QUALIFIERS)
def test_link_grouping_structure_matches(qualifier: str) -> None:
    """Columns grouped by the template are the ones the catalog grouped."""
    mapping = name_map(qualifier)
    schema = resolve_schema(TEMPLATE_DIR, qualifier)

    def groups(pairs: list[tuple[str, tuple[str, Any]]]) -> dict[tuple[str, Any], set[str]]:
        out: dict[tuple[str, Any], set[str]] = {}
        for name, key in pairs:
            if all(key):
                out.setdefault(key, set()).add(name)
        return out

    template_groups = groups([(c.stubs[0].name, (c.link_fn, c.link_id))
                              for c in schema.columns])
    catalog_groups = groups([(c.stubs[0].name,
                              (mapping[c.stubs[0].name][0].link,
                               mapping[c.stubs[0].name][0].link_id))
                             for c in schema.columns])
    assert (sorted(template_groups.values(), key=sorted)
            == sorted(catalog_groups.values(), key=sorted))
