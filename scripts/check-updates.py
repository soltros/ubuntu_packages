#!/usr/bin/env python3
"""Check the Ubuntu manifest directly; never misreport failed checks as current."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import sys
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


def check(p):
    track=p.get('track')
    if not track: return dict(status='local',current=p['version'],latest='bundled source')
    kind=track['kind'];current=p['version']
    if kind=='commit':
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
    return dict(status='current' if same else 'update',current=current,latest=latest)


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
    return text


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,default=Path('update-report.md'));a.add_argument('--json-output',type=Path,default=Path('update-report.json'));args=a.parse_args()
    rows=scan(json.loads((ROOT/'packages.json').read_text()));body=report(rows);print(body)
    args.output.write_text(body);args.json_output.write_text(json.dumps(rows,indent=2)+'\n')
    if os.getenv('GITHUB_STEP_SUMMARY'):Path(os.environ['GITHUB_STEP_SUMMARY']).open('a').write(body)
    if os.getenv('GITHUB_OUTPUT'):Path(os.environ['GITHUB_OUTPUT']).open('a').write('attention='+str(any(r['status'] in ['update','error'] for r in rows)).lower()+'\n')
    sys.exit(1 if any(r['status']=='error' for r in rows) else 0)
