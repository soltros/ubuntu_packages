import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
build=load('native_build','build.py')
audit=load('native_audit','verify-native.py')


class NativeTests(unittest.TestCase):
    def package(self,root,name,path,data):
        stage=root/'stage'
        build.write(stage,'DEBIAN/control',f'Package: {name}\nVersion: 1\nArchitecture: amd64\nMaintainer: Test <test@example.org>\nDescription: test\n')
        file=stage/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data);file.chmod(0o755)
        deb=root/'test.deb'
        subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(deb)],check=True,stdout=subprocess.DEVNULL)
        return deb

    def test_native_payload_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            deb=self.package(tmp,'xemu','usr/bin/xemu',Path('/bin/true').read_bytes())
            audit.verify(deb)

    def test_images_rejected_even_if_renamed(self):
        for filename in ['opt/payload.AppImage','usr/bin/hidden-image']:
            with self.subTest(file=filename),tempfile.TemporaryDirectory() as tmp:
                header=b'\x7fELF\x02\x01\x01\x00AI\x02'+b'\0'*20
                deb=self.package(Path(tmp),'example',filename,header)
                with self.assertRaisesRegex(ValueError,'AppImage'):audit.verify(deb)

    def test_extraction_wrapper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            deb=self.package(Path(tmp),'example','usr/bin/example',b'#!/bin/sh\nAPPIMAGE_EXTRACT_AND_RUN=1 exec /opt/image "$@"\n')
            with self.assertRaisesRegex(ValueError,'extraction-on-launch'):audit.verify(deb)

    def test_source_native_apps_require_real_elf_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            deb=self.package(Path(tmp),'lichii','usr/bin/lichii',b'#!/bin/sh\nexec /opt/lichii\n')
            with self.assertRaisesRegex(ValueError,'expected native ELF'):audit.verify(deb)

    def test_no_recipe_uses_appimage_payloads(self):
        for p in build.PACKAGES.values():
            self.assertNotEqual(p['kind'],'appimage')
            for download in p.get('downloads',{}).values():
                self.assertNotIn('.AppImage',download['url'])
        self.assertEqual(build.PACKAGES['lichii']['kind'],'cmake')
        self.assertEqual(build.PACKAGES['xemu']['kind'],'xemu')
        self.assertEqual(build.PACKAGES['recomplauncher']['kind'],'deb')

    def test_revision_will_upgrade_existing_same_version_wrappers(self):
        for name in ['lichii','xemu','recomplauncher']:
            p=build.PACKAGES[name]
            old=p['version']+'-1soltros1~stonking'
            new=build.deb_version(p,'stonking')
            self.assertEqual(0,subprocess.run(['dpkg','--compare-versions',new,'gt',old]).returncode)

    def test_recomplauncher_rename_preserves_native_payload_and_upgrades_old_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);p=build.PACKAGES['recomplauncher'];stage=tmp/'upstream'
            build.write(stage,'DEBIAN/control',f"Package: {p['upstream_deb_name']}\nVersion: {p['version']}\nArchitecture: amd64\nMaintainer: Test <test@example.org>\nDepends: libc6\nDescription: test\n")
            target=stage/'usr/bin/recomplauncher';target.parent.mkdir(parents=True);shutil.copyfile('/bin/true',target);target.chmod(0o755)
            original=tmp/'original.deb'
            subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(original)],check=True,stdout=subprocess.DEVNULL)
            with patch.object(build,'download',side_effect=lambda info,dest:shutil.copyfile(original,dest)):
                build.build('recomplauncher','amd64','stonking',tmp/'output')
            result=next((tmp/'output').glob('*.deb'));audit.verify(result)
            self.assertEqual('recomplauncher',subprocess.check_output(['dpkg-deb','-f',str(result),'Package'],text=True).strip())
            self.assertEqual('recomp-launcher',subprocess.check_output(['dpkg-deb','-f',str(result),'Conflicts'],text=True).strip())


if __name__=='__main__':unittest.main()
