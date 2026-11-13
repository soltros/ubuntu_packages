#!/usr/bin/env python3
"""Reuse only verified package-job artifacts whose recipe matches current main."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REPO = os.environ.get('REPO', 'soltros/ubuntu_packages')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


merge = load('publish_merge', ROOT / 'experiments/xemu/merge_repo.py')
publication = load('publication_versions', ROOT / 'scripts/check-publication.py')


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', 'repos/' + REPO + '/' + path], text=True))


def file_at(path, sha):
    return json.loads(base64.b64decode(api('contents/' + path + '?ref=' + sha)['content']))


def trusted_run(run, workflow):
    return (run['event'] in ['push', 'workflow_dispatch'] and run['head_branch'] == 'main'
            and run['head_repository']['full_name'] == REPO
            and run['path'] == '.github/workflows/' + workflow)


def recover(directory):
    recipes = json.loads((ROOT / 'packages.json').read_text())
    expected = publication.expected(recipes)
    current = {name: version for path in directory.glob('*.deb') for name, arch, version in [merge.fields(path)] if arch in ['amd64', 'all'] and version == expected.get(name)}
    needed = {name for name in recipes if current.get(recipes[name].get('deb_name', name)) != expected[recipes[name].get('deb_name', name)]}
    for run in api('actions/workflows/build.yml/runs?branch=main&per_page=12')['workflow_runs']:
        if not needed:
            break
        if not trusted_run(run, 'build.yml'):
            continue
        artifacts = {a['name']: a for a in api(f"actions/runs/{run['id']}/artifacts?per_page=100")['artifacts'] if not a['expired']}
        if not artifacts:
            continue
        old = file_at('packages.json', run['head_sha'])
        jobs = api(f"actions/runs/{run['id']}/jobs?per_page=100")['jobs']
        passed = {j['name'] for j in jobs if j['conclusion'] == 'success'}
        for name in sorted(needed.copy()):
            artifact = f'debs-stonking-{name}'
            if old.get(name) != recipes[name] or artifact not in artifacts or f'build ({name}, 26.10, stonking)' not in passed:
                continue
            with tempfile.TemporaryDirectory() as folder:
                subprocess.run(['gh', 'run', 'download', str(run['id']), '--repo', REPO, '--name', artifact, '--dir', folder], check=True)
                debs = list(Path(folder).rglob('*.deb'))
                package = recipes[name].get('deb_name', name)
                if len(debs) != 1 or merge.fields(debs[0]) != (package, 'amd64', expected[package]):
                    raise ValueError('Unexpected package in trusted artifact ' + artifact)
                merge.merge(directory, folder, 'full')
            print(f"Reused validated {name} artifact from run {run['id']}", flush=True)
            needed.remove(name)
    # Optimized xemu is independent of the stable recipe manifest.
    pin = json.loads((ROOT / 'experiments/xemu/package.json').read_text())
    present = any(merge.fields(p) == ('xemu-perf', 'amd64', pin['version']) for p in directory.glob('*.deb'))
    if not present:
        for run in api('actions/workflows/xemu-perf.yml/runs?branch=main&status=success&per_page=8')['workflow_runs']:
            if not trusted_run(run, 'xemu-perf.yml') or file_at('experiments/xemu/package.json', run['head_sha']) != pin:
                continue
            artifacts = api(f"actions/runs/{run['id']}/artifacts?per_page=100")['artifacts']
            if not any(a['name'] == 'debs-stonking-xemu-perf' and not a['expired'] for a in artifacts):
                continue
            with tempfile.TemporaryDirectory() as folder:
                subprocess.run(['gh', 'run', 'download', str(run['id']), '--repo', REPO, '--name', 'debs-stonking-xemu-perf', '--dir', folder], check=True)
                debs = list(Path(folder).rglob('*.deb'))
                if len(debs) != 1 or merge.fields(debs[0]) != ('xemu-perf', 'amd64', pin['version']):
                    raise ValueError('Unexpected optimized xemu package')
                merge.merge(directory, folder, 'xemu-perf')
            print(f"Reused validated xemu-perf artifact from run {run['id']}", flush=True)
            break
    if needed:
        print('No reusable matching artifact yet for: ' + ', '.join(sorted(needed)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    recover(parser.parse_args().directory)
