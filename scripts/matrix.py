#!/usr/bin/env python3
"""Select changed manifest packages; shared-only changes rebuild the full set."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def select(current, previous=None, paths=None, event='workflow_dispatch'):
    if event != 'push' or previous is None:
        return list(current)
    changed = [name for name in current if current[name] != previous.get(name)]
    if changed:
        return changed
    if any(p == 'packages.json' or p.startswith(('scripts/', 'assets/', 'sources/', 'tests/')) for p in paths or []):
        return list(current)
    return []


if __name__ == '__main__':
    current = json.loads((ROOT / 'packages.json').read_text())
    before = os.environ.get('BEFORE', '')
    previous, paths = None, None
    if os.environ.get('EVENT') == 'push' and before and set(before) != {'0'}:
        previous = json.loads(subprocess.check_output(['git', 'show', before + ':packages.json'], cwd=ROOT, text=True))
        paths = subprocess.check_output(['git', 'diff', '--name-only', before, 'HEAD'], cwd=ROOT, text=True).splitlines()
    names = select(current, previous, paths, os.environ.get('EVENT', 'workflow_dispatch'))
    print(json.dumps({'include': [{'package': name, 'ubuntu': '26.10', 'suite': 'stonking'} for name in names]}))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('should_build=' + str(bool(names)).lower() + '\n')
