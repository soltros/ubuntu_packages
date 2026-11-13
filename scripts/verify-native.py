#!/usr/bin/env python3
"""Reject AppImage payloads and extraction-on-launch wrappers in Debian packages."""
from pathlib import Path
import subprocess
import sys
import tempfile


def verify(deb):
    with tempfile.TemporaryDirectory(prefix='verify-native-') as tmp:
        root=Path(tmp)
        subprocess.run(['dpkg-deb','--extract',str(deb),str(root)],check=True)
        for path in root.rglob('*'):
            relative=path.relative_to(root)
            if path.name.lower().endswith('.appimage'):
                raise ValueError(f'{deb}: AppImage payload: {relative}')
            if path.is_symlink() or not path.is_file():
                continue
            with path.open('rb') as stream:
                header=stream.read(4096)
            if header[:4]==b'\x7fELF' and header[8:11] in (b'AI\x01',b'AI\x02'):
                raise ValueError(f'{deb}: renamed AppImage payload: {relative}')
            if header.startswith(b'#!') and (b'APPIMAGE_EXTRACT_AND_RUN' in header or b'--appimage-extract' in header):
                raise ValueError(f'{deb}: extraction-on-launch wrapper: {relative}')
        name=subprocess.check_output(['dpkg-deb','-f',str(deb),'Package'],text=True).strip()
        if name in ['lichii','xemu','recomplauncher']:
            binary=root/'usr/bin'/name
            if binary.is_symlink() or not binary.is_file():
                raise ValueError(f'{deb}: expected native ELF at /usr/bin/{name}')
            with binary.open('rb') as stream:
                magic=stream.read(4)
            if magic!=b'\x7fELF':
                raise ValueError(f'{deb}: expected native ELF at /usr/bin/{name}')
    print('Native package verified:',Path(deb).name)


if __name__=='__main__':
    if len(sys.argv)<2:raise SystemExit('Usage: verify-native.py PACKAGE.deb [...]')
    for package in sys.argv[1:]:verify(Path(package))
