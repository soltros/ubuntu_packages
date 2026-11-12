#!/usr/bin/env python3
"""Create a signed flat APT repository suitable for GitHub Release assets."""
import argparse
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
from pathlib import Path
import subprocess


def capture(*args):
    return subprocess.check_output(args, text=True)


def generate(directory, suite, key):
    directory=Path(directory).resolve()
    packages=[]
    for deb in sorted(directory.glob('*.deb')):
        fields=capture('dpkg-deb','-f',str(deb)).strip()
        # Duplicate versions/architectures are rejected instead of silently shadowing.
        identity=tuple(capture('dpkg-deb','-f',str(deb),field).strip() for field in ['Package','Version','Architecture'])
        if identity in [i for i,_ in packages]: raise ValueError('Duplicate package '+str(identity))
        data=deb.read_bytes()
        stanza=fields+f'\nFilename: {deb.name}\nSize: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\n\n'
        packages.append((identity,stanza))
    if not packages: raise ValueError('Refusing to publish an empty repository')
    data=''.join(s for _,s in packages).encode()
    (directory/'Packages').write_bytes(data)
    (directory/'Packages.gz').write_bytes(gzip.compress(data,mtime=0))
    now=datetime.now(timezone.utc)
    release=f'''Origin: Soltros Ubuntu
Label: Soltros Ubuntu
Suite: {suite}
Codename: {suite}
Date: {now.strftime('%a, %d %b %Y %H:%M:%S +0000')}
Valid-Until: {(now+timedelta(days=14)).strftime('%a, %d %b %Y %H:%M:%S +0000')}
Architectures: amd64 arm64 all
Description: Soltros packages for Ubuntu {suite}
SHA256:
'''
    for name in ['Packages','Packages.gz']:
        data=(directory/name).read_bytes()
        release+=f' {hashlib.sha256(data).hexdigest()} {len(data)} {name}\n'
    (directory/'Release').write_text(release)
    for name,opts in [('InRelease',['--clearsign']),('Release.gpg',['--armor','--detach-sign'])]:
        subprocess.run(['gpg','--batch','--yes','--pinentry-mode','loopback','--local-user',key,'--output',str(directory/name),*opts,str(directory/'Release')],check=True)
    with (directory/'soltros-archive-keyring.asc').open('wb') as out:
        subprocess.run(['gpg','--armor','--export',key],stdout=out,check=True)
    (directory/'SHA256SUMS').write_text(''.join(f'{hashlib.file_digest(p.open("rb"),"sha256").hexdigest()}  {p.name}\n' for p in sorted(directory.glob('*.deb'))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--suite',required=True);p.add_argument('--key',required=True)
    a=p.parse_args();generate(a.directory,a.suite,a.key)
