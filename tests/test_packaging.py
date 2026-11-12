import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
build=load('build','build.py');repo=load('repo','repository.py');updates=load('updates','check-updates.py')
class ManifestTests(unittest.TestCase):
    def test_manifest_uses_supported_package_builders(self):
        for name,p in build.PACKAGES.items():
            self.assertIn(p['kind'],['deb','archive','appimage','meson','vpn','extension','cargo','dub','flutter','xenia','npm'],name)
            self.assertTrue(p['architectures'],name)
            self.assertEqual(0,subprocess.run(['dpkg','--validate-version',p['version']],capture_output=True).returncode,name)
    def test_downloads_pinned(self):
        for name,p in build.PACKAGES.items():
            for arch,info in p.get('downloads',{}).items():
                self.assertEqual(64,len(info['sha256']),name);int(info['sha256'],16)
                self.assertNotIn('/latest/',info['url']);self.assertIn(arch,p['architectures'])
    def test_scanner_errors_visible(self):
        text=updates.report([dict(package='test',status='error',current='1',latest='unknown',error='offline')])
        self.assertIn('1 failed checks',text);self.assertIn('offline',text)
    def test_checksum_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'test';f.write_bytes(b'test')
            with self.assertRaises(ValueError):build.download(dict(url=f.as_uri(),sha256='0'*64),Path(tmp)/'dest')
    def test_archive_traversal_rejected(self):
        import io,tarfile
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'bad.tar'
            with tarfile.open(f,'w') as tar:
                member=tarfile.TarInfo('../escaped');member.size=1;tar.addfile(member,io.BytesIO(b'x'))
            with self.assertRaises(tarfile.FilterError):build.unpack(f,Path(tmp)/'out')
class BraveTests(unittest.TestCase):
    def test_brave_repack_drops_repository_bootstrap(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            tmp=Path(directory);stage=tmp/'upstream';out=tmp/'output'
            build.write(stage,'DEBIAN/control','Package: brave-browser\nVersion: 1.99.56\nArchitecture: amd64\nMaintainer: Test <test@example.org>\nDepends: brave-keyring, libc6\nDescription: test\n')
            build.write(stage,'DEBIAN/postinst','#!/bin/sh\nexit 1\n',0o755)
            build.write(stage,'opt/brave.com/brave/brave','fake executable\n',0o755)
            build.write(stage,'etc/cron.daily/brave-browser','upstream bootstrap\n',0o755)
            (stage/'usr/bin').mkdir(parents=True)
            (stage/'usr/bin/brave-browser').symlink_to('/opt/brave.com/brave/brave')
            deb=tmp/'upstream.deb'
            subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(deb)],check=True,stdout=subprocess.DEVNULL)
            def fake_download(info,dest): shutil.copy2(deb,dest)
            with patch.object(build,'download',side_effect=fake_download):
                build.build('brave','amd64','stonking',out)
            result=next(out.glob('*.deb'))
            depends=subprocess.check_output(['dpkg-deb','-f',str(result),'Depends'],text=True)
            self.assertNotIn('brave-keyring',depends)
            extract=tmp/'extract'
            subprocess.run(['dpkg-deb','--raw-extract',str(result),str(extract)],check=True)
            self.assertFalse((extract/'DEBIAN/postinst').exists())
            self.assertFalse((extract/'etc/cron.daily/brave-browser').exists())
            self.assertFalse((extract/'usr/bin/brave-browser').is_symlink())
            self.assertIn('/opt/brave.com/brave/brave',(extract/'usr/bin/brave-browser').read_text())

class IntegrationTests(unittest.TestCase):
    def test_signed_apt_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp=Path(directory);output=tmp/'repo'
            build.build('vpn-manager','amd64','stonking',output)
            deb=next(output.glob('*.deb'))
            self.assertEqual('vpn-manager',subprocess.check_output(['dpkg-deb','-f',str(deb),'Package'],text=True).strip())
            self.assertNotIn('tailscale',subprocess.check_output(['dpkg-deb','-f',str(deb),'Depends'],text=True))
            key_home=tmp/'gpg';key_home.mkdir(mode=0o700)
            # A daemon keeps stderr open. Use a file rather than a subprocess
            # pipe, which would wait forever for EOF after the parent exits.
            log=tmp/'gpg-agent.log'
            with log.open('w') as err:
                probe=subprocess.run(['gpg-agent','--homedir',str(key_home),'--daemon'],stdout=subprocess.DEVNULL,stderr=err,timeout=30)
            if probe.returncode and "can't create socket: Operation not permitted" in log.read_text():
                self.skipTest('Host prohibits gpg-agent sockets; full signed APT test runs in Ubuntu CI')
            previous=os.environ.get('GNUPGHOME');os.environ['GNUPGHOME']=str(key_home)
            try:
                subprocess.run(['gpg','--batch','--pinentry-mode','loopback','--passphrase','','--quick-generate-key','Test <test@example.org>','ed25519','sign','1d'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                repo.generate(output,'stonking','test@example.org')
                subprocess.run(['gpg','--verify',str(output/'InRelease')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                for d in ['state/lists/partial','cache/archives/partial','download']:(tmp/d).mkdir(parents=True)
                source=tmp/'sources.list';source.write_text(f'deb [signed-by={output}/soltros-archive-keyring.asc] file:{output} ./\n')
                options=['-o','Dir::Etc::sourcelist='+str(source),'-o','Dir::Etc::sourceparts=-','-o','Dir::State='+str(tmp/'state'),'-o','Dir::Cache='+str(tmp/'cache'),'-o','Debug::NoLocking=1','-o','APT::Sandbox::User='+os.environ.get('USER','agent')]
                subprocess.run(['/usr/bin/apt-get',*options,'update'],check=True,stdout=subprocess.DEVNULL)
                subprocess.run(['/usr/bin/apt-get',*options,'download','vpn-manager'],cwd=tmp/'download',check=True,stdout=subprocess.DEVNULL)
                self.assertEqual(1,len(list((tmp/'download').glob('*.deb'))))
            finally:
                if previous is None:os.environ.pop('GNUPGHOME',None)
                else:os.environ['GNUPGHOME']=previous
