#!/usr/bin/env python3
"""Unpack the pinned Lichii AppImage at build time; ship only native files."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import build


def squashfs_offset(path):
    data = path.read_bytes()
    cursor = 0
    while True:
        offset = data.find(b'hsqs', cursor)
        if offset < 0:
            raise ValueError('No valid SquashFS superblock in AppImage')
        cursor = offset + 4
        if len(data) - offset < 96:
            continue
        major, minor = struct.unpack_from('<HH', data, offset + 28)
        size = struct.unpack_from('<Q', data, offset + 40)[0]
        if (major, minor) == (4, 0) and 96 <= size <= len(data) - offset:
            return offset


def package(arch, suite, output):
    p = build.PACKAGES['lichii']
    with tempfile.TemporaryDirectory(prefix='lichii-deb-') as folder:
        work = Path(folder)
        image = work / 'upstream.AppImage'
        build.download(p['downloads'][arch], image)
        extracted = work / 'extracted'
        build.run('unsquashfs', '-no-xattrs', '-no-progress', '-o', str(squashfs_offset(image)), '-d', extracted, image)
        source = extracted / 'usr'
        for path in source.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(extracted.resolve()):
                raise ValueError('Escaping AppDir symlink: ' + str(path))
        stage = work / 'root'
        private = stage / 'usr/lib/lichii/usr'
        shutil.copytree(source, private, symlinks=True)
        if (private / 'bin/lichii').read_bytes()[:4] != b'\x7fELF':
            raise ValueError('Extracted Lichii executable is not native ELF')
        # SquashFS extraction must not leave root-only directory modes in a DEB.
        for path in [stage, *stage.rglob('*')]:
            if not path.is_symlink():
                path.chmod(0o755 if path.is_dir() else 0o644 | (path.stat().st_mode & 0o111))
        build.launcher(stage, 'lichii', '/usr/lib/lichii/usr/bin/lichii')
        for relative in ['applications', 'icons', 'mime']:
            origin = private / 'share' / relative
            if origin.is_dir():
                shutil.copytree(origin, stage / 'usr/share' / relative, symlinks=True)
        # Resolve distro dependencies for every ELF, including Qt plugins. The
        # bundled libraries are private and need no separate apt package.
        checks = work / 'dependency-check'
        build.write(checks, 'debian/control', 'Source: lichii\nSection: games\nPriority: optional\nMaintainer: Soltros <packages@soltros.info>\n\nPackage: lichii\nArchitecture: any\nDescription: Lichii\n')
        elfs = []
        for path in private.rglob('*'):
            if path.is_file() and not path.is_symlink():
                with path.open('rb') as stream:
                    if stream.read(4) == b'\x7fELF':
                        elfs.append(path)
        deps = subprocess.check_output(['dpkg-shlibdeps', '--ignore-missing-info', '--warnings=0', '-O', '-l' + str(private / 'lib'), *['-e' + str(path) for path in elfs]], cwd=checks, text=True)
        dependencies = next(line.split('=', 1)[1] for line in deps.splitlines() if line.startswith('shlibs:Depends='))
        dependencies += ', libvulkan1, libegl1, libgl1, libpulse0, libasound2t64, libudev1, libxcb-cursor0'
        filename = build.control(stage, 'lichii', dict(p, depends=dependencies), arch, suite)
        output = output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        build.run('dpkg-deb', '--root-owner-group', '-Zxz', '--build', stage, output / filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', default='amd64')
    parser.add_argument('--suite', default='stonking')
    parser.add_argument('--output', type=Path, default=Path('dist'))
    args = parser.parse_args()
    package(args.arch, args.suite, args.output)
