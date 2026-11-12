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
    def test_every_attribute_accounted_for(self):
        migration=json.loads((ROOT/'migration.json').read_text());aliases=json.loads((ROOT/'aliases.json').read_text())
        for name in migration['attributes']+migration['extra_packages']:
            target=aliases.get(name,name)
            if target=='brave-browser':target='brave'
            self.assertTrue(target in build.PACKAGES or name in migration['excluded_by_request'],name)
    def test_exclusions(self):
        for name,p in build.PACKAGES.items():
            self.assertNotIn('nix-bin',p.get('depends',''),name)
            self.assertNotIn(name,['grayjay','keyguard','nixpkger','nixboutique','flakebuilder','flakebuilder-gui'])
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
class IntegrationTests(unittest.TestCase):
    def test_signed_apt_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp=Path(directory);output=tmp/'repo'
            build.build('vpn-manager','amd64','noble',output)
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
                repo.generate(output,'noble','test@example.org')
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
