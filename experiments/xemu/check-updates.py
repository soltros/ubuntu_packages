#!/usr/bin/env python3
"""Report source/cache-patch changes requiring an optimized package rebuild."""
import json
import os
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def fetch(path):
    headers = {'User-Agent': 'soltros-ubuntu', 'Accept': 'application/vnd.github+json'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/xemu-project/xemu/' + path, headers=headers), timeout=60) as response:
        return json.load(response)


if __name__ == '__main__':
    pin = json.loads((HERE / 'package.json').read_text())
    stable = json.loads((ROOT / 'packages.json').read_text())['xemu']
    notes = []
    try:
        latest = fetch('releases/latest')
        pr = fetch('pulls/' + str(pin['upstream_pr']))
        if latest['tag_name'].removeprefix('v') != stable['version']:
            notes.append(f"Upstream stable release is {latest['tag_name']}; review/rebase xemu-perf with the stable package update.")
        if stable['rev'] != pin['base_revision']:
            notes.append('Stable source changed; rebase/review the optimized cache patch.')
        if pr['head']['sha'] != pin['upstream_patch_revision']:
            notes.append(f"Cache PR #{pin['upstream_pr']} changed to {pr['head']['sha']}; review it and bump the experimental Debian revision.")
        if pr['merged']:
            notes.append('The upstream cache PR was merged; review whether the backport is still needed.')
        elif pr['state'] == 'closed':
            notes.append('The upstream cache PR was closed without merging; review before continuing to ship it.')
    except (OSError, KeyError, ValueError) as error:
        notes.append('Update check failed: ' + str(error))
    Path('xemu-perf-update.md').write_text('# XEMU (Optimizations) update check\n\n' + ('\n'.join('- ' + n for n in notes) if notes else 'Source and cache patch pins are current.') + '\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('attention=' + str(bool(notes)).lower() + '\n')
    print(Path('xemu-perf-update.md').read_text())
