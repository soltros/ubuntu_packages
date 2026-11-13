import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package_matrix', ROOT / 'scripts/matrix.py')
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


class MatrixTests(unittest.TestCase):
    def test_recipe_change_builds_only_that_package(self):
        before = {'lichii': {'version': '1'}, 'xemu': {'version': '1'}}
        after = dict(before, lichii={'version': '2'})
        self.assertEqual(matrix.select(after, before, ['packages.json', 'scripts/build.py'], 'push'), ['lichii'])

    def test_shared_only_changes_rebuild_everything_and_workflow_only_does_not(self):
        packages = {'lichii': {}, 'xemu': {}}
        self.assertEqual(matrix.select(packages, packages, ['scripts/build.py'], 'push'), list(packages))
        self.assertEqual(matrix.select(packages, packages, ['.github/workflows/publish.yml'], 'push'), [])
        self.assertEqual(matrix.select(packages, packages, [], 'workflow_dispatch'), list(packages))
