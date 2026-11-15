#!/usr/bin/env python3
"""Build a checksum-verified, desktop-integrated HelloNzb DEB."""
import argparse, hashlib, json, shutil, subprocess, tempfile, urllib.request, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def write(base, path, data, executable=False):
    target=base/path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data.encode() if isinstance(data,str) else data)
    target.chmod(0o755 if executable else 0o644)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--suite',choices=['resolute','stonking'],required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--arch',choices=['amd64','arm64'],default='amd64')
    args=ap.parse_args()
    p=json.loads((ROOT/'packages.json').read_text())['hellonzb']
    if args.arch not in p['architectures']: raise SystemExit('Unsupported architecture')
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp); stage=temp/'stage';stage.mkdir()
        jar=temp/'HelloNzb.jar'
        info=p['downloads'][args.arch]
        req=urllib.request.Request(info['url'],headers={'User-Agent':'soltros-ubuntu'})
        with urllib.request.urlopen(req,timeout=120) as stream,jar.open('wb') as out:
            shutil.copyfileobj(stream,out)
        actual=hashlib.sha256(jar.read_bytes()).hexdigest()
        if actual!=info['sha256']: raise ValueError('HelloNzb SHA256 mismatch: '+actual)
        with zipfile.ZipFile(jar) as z:
            if 'me/mabra/hellonzb/HelloNzb.class' not in z.namelist(): raise ValueError('Missing main class')
            manifest=z.read('META-INF/MANIFEST.MF').decode()
            if 'Main-Class: me.mabra.hellonzb.HelloNzb' not in manifest: raise ValueError('Unexpected entry point')
            icon=z.read('resources/icons/HelloNzb_logo_linux.png')
        write(stage,'usr/share/hellonzb/HelloNzb.jar',jar.read_bytes())
        write(stage,'usr/share/icons/hicolor/48x48/apps/hellonzb.png',icon)
        write(stage,'usr/bin/hellonzb',"""#!/bin/sh
# Swing applications use XWayland when launched from a Wayland desktop.
if ! command -v java >/dev/null 2>&1; then
  echo 'HelloNzb requires Java; install default-jre.' >&2
  exit 127
fi
export _JAVA_AWT_WM_NONREPARENTING=1
exec java -Djava.awt.headless=false -jar /usr/share/hellonzb/HelloNzb.jar "$@"
""",True)
        write(stage,'usr/share/applications/hellonzb.desktop',"""[Desktop Entry]
Type=Application
Name=HelloNzb
Comment=Download NZB files from Usenet
Exec=hellonzb %F
Icon=hellonzb
Terminal=false
Categories=Network;FileTransfer;
MimeType=application/x-nzb;
StartupNotify=true
""")
        write(stage,'usr/share/mime/packages/hellonzb.xml',"""<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-nzb">
    <comment>Usenet NZB file</comment>
    <glob pattern="*.nzb"/>
  </mime-type>
</mime-info>
""")
        version=f"{p['version']}-{p.get('revision','1soltros1')}~{args.suite}"
        write(stage,'DEBIAN/control',f"""Package: hellonzb
Version: {version}
Architecture: all
Maintainer: Soltros <packages@soltros.info>
Section: net
Priority: optional
Depends: {p['depends']}
Recommends: {p['recommends']}
Description: {p['description']}
 Java Swing desktop NZB downloader packaged for Ubuntu.
""")
        args.output.mkdir(parents=True,exist_ok=True)
        dest=args.output/f'hellonzb_{version}_all.deb'
        subprocess.run(['dpkg-deb','--root-owner-group','-Zxz','--build',str(stage),str(dest)],check=True)
        print(dest)

if __name__=='__main__': main()
