import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('suite_publication',ROOT/'scripts/check-publication.py')
publication=importlib.util.module_from_spec(spec);spec.loader.exec_module(publication)


class SuiteTests(unittest.TestCase):
    def test_matrix_includes_every_recipe_for_both_containers(self):
        env=dict(os.environ,EVENT='workflow_dispatch')
        env.pop('GITHUB_OUTPUT',None)
        rows=json.loads(subprocess.check_output(['python3',str(ROOT/'scripts/matrix.py')],env=env,text=True))['include']
        recipes=json.loads((ROOT/'packages.json').read_text())
        for suite,ubuntu in [('resolute','26.04'),('stonking','26.10')]:
            self.assertEqual({r['package'] for r in rows if r['suite']==suite},set(recipes))
            self.assertTrue(all(r['ubuntu']==ubuntu for r in rows if r['suite']==suite))

    def test_new_release_cannot_be_satisfied_by_other_suite_source_debs(self):
        packages={'app':{'kind':'archive','version':'1'}}
        index='Package: app\nVersion: 1-1soltros1~stonking\nArchitecture: amd64\n\n'
        self.assertFalse(publication.missing_versions(packages,index,'stonking'))
        self.assertEqual(publication.missing_versions(packages,index,'resolute'),['app=1-1soltros1~resolute'])
