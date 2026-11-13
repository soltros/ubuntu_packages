#!/usr/bin/env python3
"""Overlay validated package artifacts without dropping unrelated APT packages."""
import argparse
from pathlib import Path
import shutil
import subprocess


def fields(deb):
    return tuple(subprocess.check_output(['dpkg-deb', '-f', str(deb), key], text=True).strip() for key in ['Package', 'Architecture', 'Version'])


def merge(existing, incoming, mode):
    additions = list(Path(incoming).rglob('*.deb'))
    if not additions:
        raise ValueError('Refusing empty package artifacts')
    identities = [fields(deb) for deb in additions]
    if mode == 'xemu-perf' and (len(additions) != 1 or identities[0][:2] != ('xemu-perf', 'amd64')):
        raise ValueError('Optimized workflow may publish only one amd64 xemu-perf package')
    keys = [(name, arch) for name, arch, _ in identities]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate incoming package/architecture')
    if mode == 'full' and any(name == 'xemu-perf' for name, _, _ in identities):
        raise ValueError('Full workflow cannot overwrite independently built xemu-perf')
    existing = Path(existing)
    existing.mkdir(parents=True, exist_ok=True)
    current = [(deb, fields(deb)) for deb in existing.glob('*.deb')]
    # A stale optimized build must never replace a newer published version.
    for _, (name, arch, version) in current:
        for n, a, v in identities:
            if (name, arch) == (n, a) and subprocess.run(['dpkg', '--compare-versions', version, 'gt', v]).returncode == 0:
                raise ValueError(f'Refusing downgrade of {name}: {version} -> {v}')
    for deb, (name, arch, _) in current:
        if (name, arch) in keys or (mode == 'full' and name != 'xemu-perf'):
            deb.unlink()
    for deb in additions:
        shutil.copy2(deb, existing / deb.name)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('existing', type=Path)
    p.add_argument('incoming', type=Path)
    p.add_argument('--mode', required=True, choices=['full', 'xemu-perf'])
    a = p.parse_args()
    merge(a.existing, a.incoming, a.mode)
