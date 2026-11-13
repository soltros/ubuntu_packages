#!/usr/bin/env python3
"""Keep update issues open until the exact pinned versions reach signed APT."""
import json
import os
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
URL='https://github.com/soltros/ubuntu_packages/releases/download/apt-stonking/Packages'


def expected(packages):
    result={}
    for name,p in packages.items():
        version=p['version']
        if p['kind']!='deb' or name=='brave' or p.get('repackage'):
            version+='-'+p.get('revision','1soltros1')+'~stonking'
        result[p.get('deb_name',name)]=version
    return result


def missing_versions(packages,index):
    published={}
    for paragraph in index.split('\n\n'):
        fields={}
        for line in paragraph.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                key,value=line.split(': ',1);fields[key]=value
        if fields.get('Architecture') in ['amd64','all']:
            published.setdefault(fields.get('Package'),set()).add(fields.get('Version'))
    return [f'{name}={version}' for name,version in expected(packages).items() if version not in published.get(name,set())]


if __name__=='__main__':
    packages=json.loads((ROOT/'packages.json').read_text())
    try:
        with urllib.request.urlopen(URL,timeout=30) as response:index=response.read().decode()
        missing=missing_versions(packages,index)
        ready=not missing
        print('Published manifest matches pins.' if ready else 'Waiting for signed APT publication: '+', '.join(missing))
    except OSError as error:
        ready=False
        print('Cannot confirm APT publication:',error)
    if os.environ.get('GITHUB_OUTPUT'):
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:stream.write('ready='+str(ready).lower()+'\n')
