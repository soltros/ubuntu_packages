import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('catalogue',HERE/'package-list.py')
docs=importlib.util.module_from_spec(spec);spec.loader.exec_module(docs)


class CatalogueTests(unittest.TestCase):
    def test_new_definition_updates_install_name_version_architecture_and_count(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for path in ['scripts','experiments/xemu']:(root/path).mkdir(parents=True)
            (root/'scripts/suites.json').write_text(json.dumps({'resolute':'26.04','stonking':'26.10'}))
            (root/'experiments/xemu/package.json').write_text(json.dumps({'version':'1-1~stonking'}))
            (root/'packages.json').write_text(json.dumps({'new-app':{'deb_name':'actual-install-name','description':'A | B','version':'2.3','architectures':['amd64','arm64'],'kind':'deb','track':{'kind':'release'}}}))
            text=docs.catalogue(root)
            for value in ['1 standard definitions','`actual-install-name`','2.3','amd64, arm64','A \\| B','daily assigned issue','`xemu-perf`','26.04','26.10']:
                self.assertIn(value,text)
            (root/'packages.json').write_text('{}')
            text=docs.catalogue(root)
            self.assertNotIn('actual-install-name',text)
            self.assertIn('0 standard definitions',text)

    def test_regeneration_preserves_other_readme_content_and_is_repeatable(self):
        text='Intro\n'+docs.START+'\nold list\n'+docs.END+'\nOther docs\n'
        result=docs.updated(text,'new list')
        self.assertTrue(result.startswith('Intro\n'))
        self.assertTrue(result.endswith('\nOther docs\n'))
        self.assertEqual(result,docs.updated(result,'new list'))
