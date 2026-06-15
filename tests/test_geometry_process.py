################################################################################
# tests/test_geometry_process.py: get_args + process_tables walk.
################################################################################
import types

from filecache import FCPath

from metadata_tools.geometry_support import process as proc


def _args(tree, **over):
    ns = types.SimpleNamespace(
        metadata_tree=str(tree), output_tree=str(tree), new_only=False,
        labels=False, volumes=None, selection='S', first=None, sampling=8,
        pattern=None)
    for k, v in over.items():
        setattr(ns, k, v)
    return ns


def _tree(tmp_path):
    root = tmp_path / 'GO_0xxx'
    for vol in ('GO_0001', 'GO_0002'):
        (root / vol).mkdir(parents=True)
    return FCPath(root)


#===============================================================================
# get_args
#===============================================================================
def test_get_args_defaults_and_parse():
    parser = proc.get_args(host='GO', selection='S', sampling=8)
    args = parser.parse_args(['/meta', '/out', '--selection', 'SD',
                              '--sampling', '4'])
    assert args.selection == 'SD'
    assert args.sampling == 4


#===============================================================================
# process_tables
#===============================================================================
def test_process_tables_task_list_only(monkeypatch, tmp_path):
    tree = _tree(tmp_path)
    added = []
    monkeypatch.setattr(proc.com, 'add_task', lambda vol, t: added.append(vol))
    monkeypatch.setattr(proc.com, 'write_task_file', lambda f: None)
    proc.process_tables('GO_0xxx_supplemental_index', args=_args(tree),
                        task_list_only=True, task_file='tasks.json')
    assert sorted(added) == ['GO_0001', 'GO_0002']


def test_process_tables_builds_suite(monkeypatch, tmp_path):
    tree = _tree(tmp_path)
    built = []

    class FakeSuite:
        def __init__(self, indir, outdir, template_path, metadata_dir, **kwargs):
            built.append(FCPath(indir).name)

        def create(self, labels_only=False, pattern=None):
            built.append('created')

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index', args=_args(tree))
    assert 'GO_0001' in built
    assert built.count('created') == 2


def test_process_tables_excludes_volume(monkeypatch, tmp_path):
    tree = _tree(tmp_path)
    built = []

    class FakeSuite:
        def __init__(self, indir, *a, **k):
            built.append(FCPath(indir).name)

        def create(self, **k):
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index', args=_args(tree),
                        exclude=['GO_0002'])
    assert built == ['GO_0001']


def test_process_tables_volumes_filter(monkeypatch, tmp_path):
    tree = _tree(tmp_path)
    built = []

    class FakeSuite:
        def __init__(self, indir, *a, **k):
            built.append(FCPath(indir).name)

        def create(self, **k):
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index', args=_args(tree),
                        volumes=['GO_0001'])
    assert built == ['GO_0001']
