#!/usr/bin/env python3
"""Build the pinned cache backport as a side-by-side native xemu-perf DEB."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('package_builder', ROOT / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def repackage(deb, output, version):
    with tempfile.TemporaryDirectory() as folder:
        stage = Path(folder)
        builder.run('dpkg-deb', '--raw-extract', deb, stage)
        binary = stage / 'usr/bin/xemu'
        if binary.read_bytes()[:4] != b'\x7fELF':
            raise ValueError('Upstream build did not produce a native ELF')
        destination = stage / 'usr/lib/xemu-perf/xemu'
        destination.parent.mkdir(parents=True)
        binary.rename(destination)
        shutil.copy2(HERE / 'launcher.py', binary.with_name('xemu-perf'))
        binary.with_name('xemu-perf').chmod(0o755)
        for icon in list((stage / 'usr/share/icons').rglob('xemu.*')):
            icon.rename(icon.with_name('xemu-perf' + icon.suffix))
        desktop = stage / 'usr/share/applications/xemu.desktop'
        desktop.unlink()
        builder.write(stage, 'usr/share/applications/xemu-perf.desktop', '[Desktop Entry]\nType=Application\nName=XEMU (Optimizations)\nComment=Experimental Vulkan cache build of the original Xbox emulator\nExec=xemu-perf\nIcon=xemu-perf\nTerminal=false\nCategories=Game;Emulator;\n')
        doc = stage / 'usr/share/doc/xemu'
        doc.rename(doc.with_name('xemu-perf'))
        shutil.copy2(HERE / 'README.md', doc.with_name('xemu-perf') / 'README.optimizations.md')
        control = stage / 'DEBIAN/control'
        text = control.read_text()
        text = re.sub(r'(?m)^Package: .*$', 'Package: xemu-perf', text)
        text = re.sub(r'(?m)^Version: .*$', 'Version: ' + version, text)
        if re.search(r'(?m)^Depends: ', text):
            text = re.sub(r'(?m)^Depends: ', 'Depends: python3, ', text)
        else:
            text = text.rstrip() + '\nDepends: python3\n'
        control.write_text(text)
        md5 = []
        for path in sorted(stage.rglob('*')):
            if path.is_file() and not path.is_symlink() and path.relative_to(stage).parts[0] != 'DEBIAN':
                md5.append(f'{hashlib.md5(path.read_bytes()).hexdigest()}  {path.relative_to(stage)}')
        (stage / 'DEBIAN/md5sums').write_text('\n'.join(md5) + '\n')
        arch = subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Architecture'], text=True).strip()
        output.mkdir(parents=True, exist_ok=True)
        result = output / f'xemu-perf_{version}_{arch}.deb'
        builder.run('dpkg-deb', '--root-owner-group', '-Zxz', '--build', stage, result)
        return result


def main():
    suite = os.environ.get('SUITE', 'stonking')
    if suite not in ['resolute', 'stonking']: raise ValueError('Unsupported suite')
    metadata = json.loads((HERE / 'package.json').read_text())
    p = json.loads((ROOT / 'packages.json').read_text())['xemu']
    if p['rev'] != metadata['base_revision']:
        raise ValueError('Stable xemu source changed. Rebase and review the experimental patch before building.')
    patch = HERE / 'vulkan-cache.patch'
    if hashlib.sha256(patch.read_bytes()).hexdigest() != metadata['patch_sha256']:
        raise ValueError('Experimental patch hash mismatch')
    with tempfile.TemporaryDirectory(prefix='xemu-perf-') as folder:
        work = Path(folder)
        src = builder.source(p, work / 'source')
        builder.run('git', 'apply', '--check', patch, cwd=src)
        builder.run('git', 'apply', patch, cwd=src)
        original = work / 'debs'
        original.mkdir()
        builder.native_source_deb(src, p, 'xemu', suite, original)
        debs = list(original.glob('xemu_*.deb'))
        if len(debs) != 1:
            raise ValueError('Expected exactly one native xemu DEB')
        result = repackage(debs[0], ROOT / 'dist', metadata['version'].split('~')[0]+'~'+suite)
        print('Built', result)


if __name__ == '__main__':
    main()
