import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publication',ROOT/'scripts/check-publication.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PublicationTests(unittest.TestCase):
    def test_native_deb_and_rebuilt_revision_have_different_expected_versions(self):
        packages={'fresh':{'kind':'deb','deb_name':'fresh-editor','version':'0.5.8-1'},'xemu':{'kind':'xemu','version':'0.8.139','revision':'2soltros1'},'brave':{'kind':'deb','deb_name':'brave-browser','version':'1.99.57'}}
        expected=p.expected(packages)
        self.assertEqual(expected['fresh-editor'],'0.5.8-1')
        self.assertEqual(expected['xemu'],'0.8.139-2soltros1~stonking')
        self.assertEqual(expected['brave-browser'],'1.99.57-1soltros1~stonking')
    def test_old_wrapper_does_not_close_issue(self):
        packages={'xemu':{'kind':'xemu','version':'0.8.139','revision':'2soltros1'}}
        index='Package: xemu\nVersion: 0.8.139-1soltros1~stonking\nArchitecture: amd64\n'
        self.assertTrue(p.missing_versions(packages,index))
    def test_all_versions_must_match_and_wrong_architecture_cannot_satisfy_it(self):
        packages={'example':{'kind':'deb','version':'2'}}
        for index in ['', 'Package: example\nVersion: 1\nArchitecture: amd64\n','Package: example\nVersion: 2\nArchitecture: arm64\n']:
            self.assertTrue(p.missing_versions(packages,index))
        self.assertFalse(p.missing_versions(packages,'Package: example\nVersion: 2\nArchitecture: amd64\n'))
