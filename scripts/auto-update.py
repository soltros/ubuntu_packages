#!/usr/bin/env python3
"""Refresh checksum-pinned binary recipes using the existing upstream scan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
AUTO = frozenset(('brave', 'chatgpt', 'codex', 'lichii', 'recomplauncher',
                  'sharpemu', 'waterfox', 'vacuumtube', 'fresh', 'bitwarden',
                  'zettlr', 'discord', 'silo'))
SHA256 = re.compile(r'^[a-f0-9]{64}$')


def get_json(url):
    headers = {'User-Agent': 'soltros-ubuntu-autoupdate',
               'Accept': 'application/vnd.github+json'}
    if url.startswith('https://api.github.com/') and os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                timeout=40) as response:
        return json.load(response)


def hash_download(url, deb_name=None, version=None, arch=None):
    """Hash the real download, and verify package identity where applicable."""
    with tempfile.NamedTemporaryFile(suffix='.deb' if deb_name else '.bin') as temp:
        sha = hashlib.sha256()
        req = urllib.request.Request(url,
                                     headers={'User-Agent': 'soltros-ubuntu-autoupdate'})
        with urllib.request.urlopen(req, timeout=180) as response:
            if not response.geturl().startswith('https://'):
                raise ValueError('Non-HTTPS download redirect')
            while chunk := response.read(1024 * 1024):
                sha.update(chunk)
                temp.write(chunk)
        temp.flush()
        if deb_name:
            control = subprocess.check_output(
                ['dpkg-deb', '-f', temp.name], text=True)
            fields = dict(line.split(': ', 1) for line in control.splitlines()
                          if ': ' in line and not line[0].isspace())
            actual = [fields.get('Package'), fields.get('Version'),
                      fields.get('Architecture')]
            if actual != [deb_name, version, arch]:
                raise ValueError('Upstream DEB metadata mismatch: ' + repr(actual))
        return sha.hexdigest()


def assets_for(track, latest, tag_override=None):
    tag = tag_override or track.get('prefix', '') + latest
    release = get_json('https://api.github.com/repos/' + track['repo']
                       + '/releases/tags/' + urllib.parse.quote(tag, safe=''))
    if release['tag_name'] != tag or release.get('draft'):
        raise ValueError('Release tag mismatch')
    if release.get('prerelease') and track['kind'] != 'prerelease':
        raise ValueError('Unexpected prerelease')
    return {asset['name']: asset for asset in release.get('assets', [])}


def update_one(name, p, row):
    latest, current = row['latest'], p['version']
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._~+-]*', latest) or latest == current:
        raise ValueError('Invalid new version')
    track = p['track']
    kind = track['kind']
    if kind not in ('release', 'prerelease', 'release_asset', 'chatgpt', 'discord'):
        raise ValueError('Unsupported tracking kind')
    if p['kind'] not in ('deb', 'archive', 'appdir'):
        raise ValueError('Source build requires review')
    assets = {}
    if name == 'chatgpt':
        urls = {arch: ('https://persistent.oaistatic.com/codex-app-prod/linux/deb/'
                        'pool/main/c/chatgpt/chatgpt_' + latest + '_' + arch + '.deb')
                for arch in p['architectures']}
    elif name == 'discord':
        url = row.get('url', '')
        if not url.startswith('https://stable.dl2.discordapp.net/distro/app/stable/linux/x64/'):
            raise ValueError('Unexpected Discord download host')
        urls = {'amd64': url}
    else:
        tag_override = None
        if kind == 'release_asset':
            source = row.get('url', '')
            prefix = 'https://github.com/' + track['repo'] + '/releases/download/'
            if not source.startswith(prefix):
                raise ValueError('Missing trusted release asset link')
            tag_override = urllib.parse.unquote(source[len(prefix):].split('/', 1)[0])
        assets = assets_for(track, latest, tag_override)
        urls = {}
        for arch, old in p['downloads'].items():
            previous = old['url']
            if name == 'waterfox':
                new = previous.replace('/' + current + '/', '/' + latest + '/').replace(
                    'waterfox-' + current + '.tar.bz2', 'waterfox-' + latest + '.tar.bz2')
                if previous == new or not new.startswith('https://cdn.waterfox.com/'):
                    raise ValueError('Waterfox URL format changed')
                urls[arch] = new
                continue
            filename = urllib.parse.unquote(urllib.parse.urlsplit(previous).path.rsplit('/', 1)[-1])
            new_name = filename.replace(current, latest)
            if kind == 'release_asset' and arch == 'amd64':
                new_name = urllib.parse.unquote(
                    urllib.parse.urlsplit(row['url']).path.rsplit('/', 1)[-1])
            asset = assets.get(new_name)
            if not asset:
                raise ValueError('Expected asset absent: ' + new_name)
            new = asset['browser_download_url']
            prefix = 'https://github.com/' + track['repo'] + '/releases/download/'
            if not new.startswith(prefix):
                raise ValueError('Unexpected release asset host')
            urls[arch] = new
    if set(urls) != set(p['architectures']):
        raise ValueError('Missing architecture download')
    result = json.loads(json.dumps(p))
    result['version'] = latest
    for arch, url in urls.items():
        filename = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit('/', 1)[-1])
        digest = assets.get(filename, {}).get('digest', '')
        digest = digest[7:] if digest.startswith('sha256:') else ''
        if not SHA256.fullmatch(digest):
            deb = p.get('upstream_deb_name', p.get('deb_name', name)) if p['kind'] == 'deb' else None
            digest = hash_download(url, deb_name=deb, version=latest, arch=arch)
        result['downloads'][arch] = {'url': url, 'sha256': digest}
    return result


def apply(packages, rows):
    changed, failures = [], []
    for row in rows:
        name = row['package']
        if row['status'] != 'update' or name not in AUTO or name not in packages:
            continue
        try:
            packages[name] = update_one(name, packages[name], row)
            changed.append(name)
        except Exception as exc:
            failures.append(name + ': ' + str(exc))
    return changed, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', type=Path, default=ROOT / 'packages.json')
    ap.add_argument('--report', type=Path, default=ROOT / 'update-report.json')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    packages = json.loads(args.manifest.read_text())
    rows = json.loads(args.report.read_text())
    if any(row['status'] == 'error' for row in rows):
        raise SystemExit('Upstream scanner failed: refusing automatic changes')
    changed, failures = apply(packages, rows)
    for failure in failures:
        print('Manual review required:', failure, flush=True)
    print('Updated:', ', '.join(changed) or '(none)', flush=True)
    if changed and not args.dry_run:
        args.manifest.write_text(json.dumps(packages, indent=2) + '\n')
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write('## Package updater\n\nUpdated: ' +
                          (', '.join(changed) or 'none') + '\n\n')
            if failures:
                summary.write('Manual review: ' + '; '.join(failures) + '\n')


if __name__ == '__main__':
    main()
