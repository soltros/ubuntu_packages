#!/usr/bin/env python3
"""Select changed manifest packages; shared-only changes rebuild the full set."""
import json
import importlib.util
import urllib.request
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
    suites = json.loads((ROOT/'scripts/suites.json').read_text())
    entries = [{'package': name, 'ubuntu': ubuntu, 'suite': suite} for name in names for suite, ubuntu in suites.items()]
    if os.environ.get('PENDING_ONLY') == 'true':
        spec = importlib.util.spec_from_file_location('publication', ROOT/'scripts/check-publication.py')
        publication = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publication)
        pending = {}
        for suite in suites:
            try:
                with urllib.request.urlopen(publication.URL.replace('apt-stonking', 'apt-'+suite), timeout=30) as response:
                    pending[suite] = set(publication.missing_versions(current, response.read().decode(), suite))
            except OSError:
                pending[suite] = {f'{n}={v}' for n,v in publication.expected(current,suite).items()}
        entries = [e for e in entries if any(v.startswith(current[e['package']].get('deb_name',e['package'])+'=') for v in pending[e['suite']])]
    print(json.dumps({'include': entries}))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('should_build=' + str(bool(entries)).lower() + '\n')
