import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def load(name, file):
    spec=importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

build=load('vendor_build','build.py')
updates=load('vendor_updates','check-updates.py')
NAMES=('fresh','bitwarden','zettlr','discord','browseros')


def release(tag, names, **kw):
    return dict(tag_name=tag, draft=False, prerelease=False,
                assets=[dict(name=name,browser_download_url='https://github.com/test/'+name,digest='sha256:'+'a'*64) for name in names], **kw)


class VendorDebTests(unittest.TestCase):
    def test_all_vendor_debs_are_in_stonking_matrix_and_scanner(self):
        matrix=json.loads(subprocess.check_output(['python3',str(ROOT/'scripts/matrix.py')],text=True))['include']
        for name in NAMES:
            p=build.PACKAGES[name]
            self.assertEqual(p['kind'],'deb')
            self.assertTrue(p.get('track'))
            self.assertIn(dict(package=name,ubuntu='26.10',suite='stonking'),matrix)
        self.assertEqual('fresh-editor',build.PACKAGES['fresh']['deb_name'])
        self.assertEqual('browserclaw',build.PACKAGES['browseros']['deb_name'])
        self.assertNotEqual(build.PACKAGES['browseros']['version'],build.PACKAGES['browseros']['upstream_version'])

    def test_native_packages_are_validated_and_preserved_byte_for_byte(self):
        for name in NAMES:
            with self.subTest(package=name), tempfile.TemporaryDirectory() as tmp:
                tmp=Path(tmp);stage=tmp/'upstream';output=tmp/'output'
                p=build.PACKAGES[name]
                build.write(stage,'DEBIAN/control',f"Package: {p.get('deb_name',name)}\nVersion: {p['version']}\nArchitecture: amd64\nMaintainer: Test <test@example.org>\nDescription: test\n")
                build.write(stage,'usr/share/test-payload',name+'\n')
                original=tmp/'upstream.deb'
                subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(original)],check=True,stdout=subprocess.DEVNULL)
                with patch.object(build,'download',side_effect=lambda info,dest:shutil.copyfile(original,dest)):
                    build.build(name,'amd64','stonking',output)
                result=next(output.glob('*.deb'))
                self.assertEqual(result.read_bytes(),original.read_bytes())

    def test_browseros_uses_deb_asset_version_instead_of_tag_or_chromium_version(self):
        p=build.PACKAGES['browseros']
        releases=[release('browserclaw/v0.52.0',['BrowserOS_neo_v0.52.1_amd64.deb','BrowserOS_neo_v0.52.1.1_amd64.deb'])]
        with patch.object(updates,'fetch',return_value=releases):row=updates.check(p)
        self.assertEqual(row['status'],'current')
        self.assertEqual(row['latest'],'0.52.1.1')
        self.assertIn('0.52.1.1_amd64.deb',row['url'])

    def test_bitwarden_ignores_cli_tags_and_prereleases(self):
        p=build.PACKAGES['bitwarden']
        rows=[release('cli-v999',['Bitwarden-999.0-amd64.deb']),
              release('desktop-v2026.10.4',['Bitwarden-2026.10.4-amd64.deb'])]
        pre=release('desktop-v999',['Bitwarden-999.0-amd64.deb']);pre['prerelease']=True;rows.append(pre)
        with patch.object(updates,'fetch',return_value=rows):row=updates.check(p)
        self.assertEqual(row['status'],'current')
        self.assertEqual(row['latest'],'2026.10.4')

    def test_fresh_excludes_debian_testing_flavor(self):
        p=build.PACKAGES['fresh']
        rows=[release('v0.5.8',['fresh-editor_0.5.8-1_amd64.deb','fresh-editor_99.0-1_amd64.debian-testing.deb'])]
        with patch.object(updates,'fetch',return_value=rows):row=updates.check(p)
        self.assertEqual(row['status'],'current')
        self.assertEqual(row['latest'],'0.5.8-1')

    def test_discord_official_endpoint_and_failure_reporting(self):
        p=build.PACKAGES['discord']
        with patch.object(updates,'fetch',return_value={'name':'1.0.169'}) as fetch:
            row=updates.check(p)
        self.assertEqual(row['status'],'current')
        self.assertIn('/1.0.169/Discord.deb',row['url'])
        self.assertEqual(fetch.call_args.args[0],'https://discord.com/api/updates/stable?platform=linux')
        with patch.object(updates,'fetch',side_effect=OSError('offline')):
            row=updates.scan({'discord':p})[0]
        self.assertEqual(row['status'],'error')
        self.assertIn('offline',row['error'])

    def test_tag_only_projects_skip_prerelease_tags(self):
        p=build.PACKAGES['addwater']
        with patch.object(updates,'fetch',return_value=[{'name':'v1.3'},{'name':'v1.2.1b1'},{'name':'rc1.4'},{'name':'v1.4'}]):
            row=updates.check(p)
        self.assertEqual(row['latest'],'1.4')
        self.assertEqual(row['status'],'update')

    def test_missing_release_asset_is_an_error(self):
        with patch.object(updates,'fetch',return_value=[]):
            row=updates.scan({'fresh':build.PACKAGES['fresh']})[0]
        self.assertEqual(row['status'],'error')

    def test_update_report_includes_download_and_digest(self):
        body=updates.report([dict(package='example',status='update',current='1',latest='2',url='https://github.com/example/package.deb',sha256='a'*64)])
        self.assertIn('https://github.com/example/package.deb',body)
        self.assertIn('a'*64,body)


if __name__=='__main__':unittest.main()
