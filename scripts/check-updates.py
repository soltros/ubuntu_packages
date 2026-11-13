#!/usr/bin/env python3
"""Check the Ubuntu manifest directly; never misreport failed checks as current."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import tarfile
import urllib.request
ROOT=Path(__file__).resolve().parents[1]


def fetch(url):
    headers={'User-Agent':'soltros-ubuntu-update-checker','Accept':'application/vnd.github+json'}
    if url.startswith('https://api.github.com/') and os.environ.get('GH_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
        return json.load(response)


def chatgpt_version():
    url='https://persistent.oaistatic.com/codex-app-prod/linux/deb/latest/chatgpt_amd64.deb'
    req=urllib.request.Request(url,headers={'User-Agent':'soltros-ubuntu','Range':'bytes=0-1048575'})
    with urllib.request.urlopen(req,timeout=30) as res: data=res.read(1048576)
    if not data.startswith(b'!<arch>\n'): raise ValueError('Invalid Debian archive')
    offset=8
    while offset+60<=len(data):
        header=data[offset:offset+60]; size=int(header[48:58]); body=data[offset+60:offset+60+size]
        offset+=60+size+(size%2)
        if b'control.tar' in header[:16]:
            with tarfile.open(fileobj=io.BytesIO(body)) as tar:
                member=next(m for m in tar.getmembers() if m.name in ['control','./control'])
                for line in tar.extractfile(member).read().decode().splitlines():
                    if line.startswith('Version: '):return line[9:]
    raise ValueError('No version found in upstream control archive')


def release_asset(track):
    """Find stable desktop DEBs, independent of unrelated tags or CLI releases."""
    releases=fetch(f"https://api.github.com/repos/{track['repo']}/releases?per_page=100")
    pattern=re.compile(track['asset_pattern'])
    candidates=[]
    for release in releases:
        if release.get('draft') or release.get('prerelease'):
            continue
        if not release['tag_name'].startswith(track.get('tag_prefix','')):
            continue
        for asset in release.get('assets',[]):
            match=pattern.fullmatch(asset['name'])
            if match:
                version=match['version']
                subprocess.run(['dpkg','--validate-version',version],check=True,capture_output=True)
                candidates.append((version,asset))
    if not candidates:
        raise ValueError('No stable Debian release asset matched '+track['asset_pattern'])
    best=candidates[0]
    for item in candidates[1:]:
        newer=subprocess.run(['dpkg','--compare-versions',item[0],'gt',best[0]],capture_output=True)
        if newer.returncode not in (0,1):
            raise ValueError('Invalid release asset version')
        if newer.returncode==0:
            best=item
    version,asset=best
    extra={'url':asset['browser_download_url']}
    if (asset.get('digest') or '').startswith('sha256:'):
        extra['sha256']=asset['digest'].split(':',1)[1]
    return version,extra


def check(p):
    track=p.get('track')
    if not track: return dict(status='local',current=p['version'],latest='bundled source')
    kind=track['kind'];current=p.get('upstream_version',p['version']);extra={}
    if kind=='release_asset':
        latest,extra=release_asset(track);same=latest==current
    elif kind=='discord':
        latest=fetch('https://discord.com/api/updates/stable?platform=linux')['name']
        if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)+',latest):raise ValueError('Invalid Discord version')
        same=latest==current
        extra['url']=f'https://stable.dl2.discordapp.net/distro/app/stable/linux/x64/{latest}/Discord.deb'
    elif kind=='commit':
        current=p['rev'];latest=fetch(f"https://api.github.com/repos/{track['repo']}/commits/{track['branch']}")['sha']
        same=latest.startswith(current)
    elif kind=='chatgpt':
        latest=chatgpt_version();same=latest==current
    else:
        endpoint='releases?per_page=100' if kind=='prerelease' else 'releases/latest'
        rel=fetch(f"https://api.github.com/repos/{track['repo']}/{endpoint}")
        if isinstance(rel,list):rel=next(x for x in rel if not x['draft'])
        if rel.get('draft') or (kind!='prerelease' and rel.get('prerelease')):raise ValueError('Unexpected release channel')
        tag=rel['tag_name'];prefix=track.get('prefix','')
        latest=tag.removeprefix(prefix);same=latest==current
    return dict(status='current' if same else 'update',current=current,latest=latest,**extra)


def scan(packages):
    rows=[]
    for name,p in packages.items():
        try: row=check(p)
        except Exception as e: row=dict(status='error',current=p['version'],latest='unknown',error=str(e))
        rows.append(dict(package=name,**row))
    return rows


def report(rows):
    updates=sum(r['status']=='update' for r in rows);errors=sum(r['status']=='error' for r in rows)
    text=f'# Ubuntu package update scan\n\n{updates} updates; {errors} failed checks.\n\n| Package | Status | Current | Latest |\n|---|---|---|---|\n'
    for r in rows:
        text+=f"| {r['package']} | {r['status']} | {r['current']} | {r['latest']} |\n"
    for r in rows:
        if r.get('error'):text+=f"\n- {r['package']}: {r['error']}\n"
    references=[r for r in rows if r.get('url') and r['status']=='update']
    if references:
        text+='\n## Debian downloads to review\n'
        for r in references:
            text+=f"\n- {r['package']}: {r['url']}"
            if r.get('sha256'):text+=f" (upstream SHA256: `{r['sha256']}`)"
            text+='\n'
    return text


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,default=Path('update-report.md'));a.add_argument('--json-output',type=Path,default=Path('update-report.json'));args=a.parse_args()
    rows=scan(json.loads((ROOT/'packages.json').read_text()));body=report(rows);print(body)
    args.output.write_text(body);args.json_output.write_text(json.dumps(rows,indent=2)+'\n')
    if os.getenv('GITHUB_STEP_SUMMARY'):Path(os.environ['GITHUB_STEP_SUMMARY']).open('a').write(body)
    if os.getenv('GITHUB_OUTPUT'):Path(os.environ['GITHUB_OUTPUT']).open('a').write('attention='+str(any(r['status'] in ['update','error'] for r in rows)).lower()+'\n')
    sys.exit(1 if any(r['status']=='error' for r in rows) else 0)
