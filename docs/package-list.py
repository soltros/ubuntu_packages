#!/usr/bin/env python3
"""Generate the README package catalogue from the actual package definitions."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- BEGIN GENERATED PACKAGE LIST -->'
END = '<!-- END GENERATED PACKAGE LIST -->'
METHODS = {'deb': 'Upstream native DEB', 'archive': 'Upstream native binary archive', 'appdir': 'AppImage unpacked in CI; native files in DEB', 'meson': 'Meson source build', 'vpn': 'Bundled Python app', 'extension': 'GNOME Shell extension', 'dub': 'D source build', 'xenia': 'Native Linux source build', 'cmake': 'CMake source build', 'xemu': 'Native source build with upstream Debian rules', 'npm': 'Electron source build'}


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def catalogue(root=ROOT):
    packages = json.loads((root/'packages.json').read_text())
    suites = json.loads((root/'scripts/suites.json').read_text())
    lines = [f'**{len(packages)} standard definitions in [packages.json](packages.json), plus the independently built `xemu-perf` definition.**', '',
             'Targets: '+', '.join(f'Ubuntu/Kubuntu {version} (`{suite}`)' for suite,version in suites.items())+'. Each release must pass its own CI checks before publication.', '',
             '| Install name | Description | Pinned version | Architectures | Packaging | Update tracking | Definition |',
             '|---|---|---|---|---|---|---|']
    for name,p in sorted(packages.items(),key=lambda item:item[1].get('deb_name',item[0])):
        method = METHODS[p['kind']]
        if p.get('repackage') or name == 'brave': method += '; adapted for existing package identity/repository'
        tracking = p.get('track')
        update = ('Upstream '+tracking['kind']+'; daily assigned issue') if tracking else 'Locally maintained source'
        values = [f"`{p.get('deb_name',name)}`",p['description'],p['version'],', '.join(p['architectures']),method,update,'[packages.json](packages.json)']
        lines.append('| '+' | '.join(cell(v) for v in values)+' |')
    experimental = json.loads((root/'experiments/xemu/package.json').read_text())
    lines.append('| `xemu-perf` | XEMU (Optimizations) | '+cell(experimental['version'].split('~')[0])+' (+ target suite) | amd64 | Native source build with pinned Vulkan cache patch | Dedicated daily source/patch checks and assigned issue | [package.json](experiments/xemu/package.json) |')
    lines += ['', 'Versions above are definition pins, not a claim that every build has been published. Check the matching [signed release](https://github.com/soltros/ubuntu_packages/releases) for availability.', '',
              'The [`sources/`](sources/) directory holds locally maintained applications. Download hashes, build dependencies, and upstream tracking are recorded in the linked definitions.']
    return '\n'.join(lines)


def updated(text, generated):
    if text.count(START)!=1 or text.count(END)!=1:
        raise ValueError('README must contain exactly one package catalogue marker pair')
    before, rest = text.split(START)
    _, after = rest.split(END)
    return before+START+'\n\n'+generated+'\n\n'+END+after


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    path=ROOT/'README.md'
    text=path.read_text(); result=updated(text,catalogue())
    if args.check:
        if text!=result: raise SystemExit('README package list is stale. Run: python3 docs/package-list.py')
        print('README package definitions are current.')
    else:
        path.write_text(result)
