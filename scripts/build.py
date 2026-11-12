#!/usr/bin/env python3
"""Build a pinned Ubuntu Debian package. Run inside the target Ubuntu release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = json.loads((ROOT / 'packages.json').read_text())


def run(*args, cwd=None, env=None):
    subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True)


def write(root, path, text, mode=0o644):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_symlink(): p.unlink()
    p.write_text(text)
    p.chmod(mode)


def copytree(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', '__pycache__'))


def download(info, dest):
    # Never send a GitHub API token to third-party download hosts.
    req = urllib.request.Request(info['url'], headers={'User-Agent': 'soltros-ubuntu'})
    with urllib.request.urlopen(req, timeout=120) as response, dest.open('wb') as out:
        shutil.copyfileobj(response, out)
    with dest.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != info['sha256']:
        raise ValueError(f"SHA256 mismatch for {info['url']}: {actual}")


def unpack(archive, dest, strip=0):
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        # data filter rejects traversal, device files and escaping symlinks.
        members = []
        for m in tar.getmembers():
            parts = Path(m.name).parts[strip:]
            if not parts:
                continue
            m.name = str(Path(*parts))
            members.append(m)
        tar.extractall(dest, members=members, filter='data')


def source(p, dest):
    if 'local' in p:
        copytree(ROOT / p['local'], dest)
    else:
        run('git', 'init', '-q', dest)
        run('git', 'remote', 'add', 'origin', 'https://github.com/' + p['repo'] + '.git', cwd=dest)
        # Abbreviated original revisions need a full clone to resolve unadvertised objects.
        if re.fullmatch(r'[a-f0-9]{7,39}', p['rev']):
            run('git', 'fetch', '--quiet', 'origin', cwd=dest)
            run('git', 'checkout', '--quiet', p['rev'], cwd=dest)
        else:
            run('git', 'fetch', '--quiet', '--depth=1', 'origin', p['rev'], cwd=dest)
            run('git', 'checkout', '--quiet', 'FETCH_HEAD', cwd=dest)
    return dest / p.get('subdir', '')


def desktop(stage, name, entry=None):
    write(stage, f'usr/share/applications/{name}.desktop',
          f'[Desktop Entry]\nType=Application\nName={name}\nExec={entry or name} %U\nTerminal=false\nCategories=Utility;\n')


def launcher(stage, name, entry, *, env=None, chdir=None):
    import shlex
    lines = ['#!/bin/sh']
    if chdir:
        lines.append('cd ' + shlex.quote(chdir) + ' || exit 1')
    for key, value in (env or {}).items():
        lines.append('export ' + key + '=' + shlex.quote(value))
    lines.append('exec ' + shlex.quote(entry) + ' "$@"')
    write(stage, 'usr/bin/' + name, '\n'.join(lines) + '\n', 0o755)


def control(stage, name, p, arch, suite):
    package = p.get('deb_name', name)
    version = p['version'] + '-1soltros1~' + suite
    text = f'Package: {package}\nVersion: {version}\nArchitecture: {arch}\nMaintainer: Soltros <packages@soltros.info>\nSection: utils\nPriority: optional\n'
    if p.get('depends'):
        text += 'Depends: ' + p['depends'] + '\n'
    if p.get('recommends'):
        text += 'Recommends: ' + p['recommends'] + '\n'
    size = sum(x.stat().st_size for x in stage.rglob('*') if x.is_file())
    text += f'Installed-Size: {(size + 1023)//1024}\nDescription: {p["description"]}\n Ubuntu package maintained by Soltros.\n'
    write(stage, 'DEBIAN/control', text)
    hashes = []
    for f in sorted(stage.rglob('*')):
        if f.is_file() and not f.is_symlink() and 'DEBIAN' not in f.relative_to(stage).parts:
            hashes.append(f'{hashlib.md5(f.read_bytes()).hexdigest()}  {f.relative_to(stage)}')
    write(stage, 'DEBIAN/md5sums', '\n'.join(hashes) + '\n')
    return f'{package}_{version}_{arch}.deb'


def meson_build(src, stage, p, name, suite, work, output):
    """Use debhelper so ELF dependency versions, triggers, and stripping are correct."""
    # Debian helper uses the caller's control file, not upstream packaging.
    shutil.rmtree(src / 'debian', ignore_errors=True)
    write(src, 'debian/control', f'''Source: {name}
Section: utils
Priority: optional
Maintainer: Soltros <packages@soltros.info>
Build-Depends: {p['build_depends']}
Standards-Version: 4.7.0
Rules-Requires-Root: no

Package: {name}
Architecture: any
Depends: ${{shlibs:Depends}}, ${{misc:Depends}}{', ' + p['depends'] if p.get('depends') else ''}
Description: {p['description']}
 Ubuntu package maintained by Soltros.
''')
    write(src, 'debian/changelog', f"{name} ({p['version']}-1soltros1~{suite}) {suite}; urgency=medium\n\n  * Port package to Ubuntu.\n\n -- Soltros <packages@soltros.info>  Thu, 12 Nov 2026 12:00:00 +0000\n")
    write(src, 'debian/source/format', '3.0 (quilt)\n')
    opts = ' '.join(p.get('meson_options', []))
    rules = '#!/usr/bin/make -f\n%:\n\tdh $@ --buildsystem=meson\n\noverride_dh_auto_configure:\n\tdh_auto_configure -- --prefix=/usr ' + opts + '\n'
    rules += '\noverride_dh_auto_test:\n\txvfb-run -a dh_auto_test\n' if name=='pantheon-studio' else ''
    write(src, 'debian/rules', rules, 0o755)
    write(src, 'debian/copyright', 'Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n\nFiles: *\nCopyright: upstream authors\nLicense: upstream\n See upstream COPYING or LICENSE shipped with this source tree.\n')
    run('dpkg-buildpackage', '-b', '-us', '-uc', cwd=src)
    artifacts = list(src.parent.glob('*.deb'))
    if not artifacts:
        raise RuntimeError('No debhelper build artifacts')
    for f in artifacts:
        shutil.copy2(f, output / f.name)


def build(name, arch, suite, output, allow_restricted=False):
    p = PACKAGES[name]
    if not p.get('redistribute', True) and not allow_restricted:
        raise ValueError(p['reason'])
    if arch not in p['architectures']:
        raise ValueError(f'{name} does not support {arch}')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=name+'-') as tmp:
        work = Path(tmp); stage = work / 'root'; stage.mkdir()
        kind = p['kind']
        if kind in ('deb', 'archive', 'appimage'):
            payload = work / 'download'
            download(p['downloads'][arch], payload)
            if kind == 'deb':
                got_name = subprocess.check_output(['dpkg-deb', '-f', str(payload), 'Package'], text=True).strip()
                got_version = subprocess.check_output(['dpkg-deb', '-f', str(payload), 'Version'], text=True).strip()
                got_arch = subprocess.check_output(['dpkg-deb', '-f', str(payload), 'Architecture'], text=True).strip()
                if (got_name,got_version,got_arch)!=(p.get('deb_name',name),p['version'],arch):
                    raise ValueError('Downloaded Debian package metadata does not match manifest')
                if name != 'brave':
                    shutil.copy2(payload, output / f'{got_name}_{got_version}_{arch}.deb')
                    return
                # Upstream Brave requires its repository keyring and bootstrap
                # scripts. This archive uses its own APT key and source instead.
                run('dpkg-deb', '--raw-extract', payload, stage)
                ctl=stage/'DEBIAN/control'
                text=ctl.read_text()
                text=re.sub(r'(?m)^Version: .*$', 'Version: '+p['version']+'-1soltros1~'+suite, text)
                text=re.sub(r'(?m)^Depends: brave-keyring, ', 'Depends: ', text)
                ctl.write_text(text)
                for script in ['postinst','postrm','prerm','preinst']:
                    (stage/'DEBIAN'/script).unlink(missing_ok=True)
                for pattern in ['etc/cron.daily/*brave*','etc/apt/sources.list.d/*brave*','opt/brave.com/brave/cron/*']:
                    for f in stage.glob(pattern):
                        if f.is_file() or f.is_symlink(): f.unlink()
                launcher(stage,'brave-browser','/opt/brave.com/brave/brave')
                launcher(stage,'brave-browser-stable','/opt/brave.com/brave/brave')
                # Recompute package checksums after replacing the launchers.
                hashes=[]
                for f in sorted(stage.rglob('*')):
                    if f.is_file() and not f.is_symlink() and 'DEBIAN' not in f.relative_to(stage).parts:
                        hashes.append(f'{hashlib.md5(f.read_bytes()).hexdigest()}  {f.relative_to(stage)}')
                write(stage,'DEBIAN/md5sums','\n'.join(hashes)+'\n')
                run('dpkg-deb','--root-owner-group','-Zxz','--build',stage,output/f'brave-browser_{p["version"]}-1soltros1~{suite}_{arch}.deb')
                return
            install = stage / 'opt' / name
            if kind == 'appimage':
                # Keep upstream AppImage intact and extract at runtime: no FUSE or
                # executing untrusted payloads while building packages.
                install.mkdir(parents=True)
                shutil.copy2(payload, install / (name+'.AppImage'))
                (install / (name+'.AppImage')).chmod(0o755)
                launcher(stage, name, '/opt/'+name+'/'+name+'.AppImage', env={'APPIMAGE_EXTRACT_AND_RUN':'1'})
                p = dict(p, depends='libasound2t64, libgl1, libegl1, libvulkan1, libgpg-error0, libxkbcommon0, libxcb1, libx11-6, libxi6, libxrandr2, libxcursor1, libxext6, libxfixes3, libxss1, libxtst6, libwayland-client0, libfontconfig1, libfreetype6, libpulse0, libusb-1.0-0, libstdc++6, zlib1g, libgmp10, libcap2, libdecor-0-0, libfribidi0, libharfbuzz0b, libudev1, libexpat1, libsm6, libice6')
            else:
                unpack(payload, install, p.get('strip',0))
                entry = install / p['entry']
                if not entry.is_file():
                    raise ValueError(f'Missing upstream executable: {entry}')
                entry.chmod(entry.stat().st_mode | 0o111)
                launcher(stage,name,'/opt/'+name+'/'+p['entry'])
                if name=='waterfox':
                    write(install,'distribution/policies.json','{"policies":{"DisableAppUpdate":true}}\n')
                    icon=install/'browser/chrome/icons/default/default128.png'
                    if icon.exists():
                        dest=stage/'usr/share/icons/hicolor/128x128/apps/waterfox.png';dest.parent.mkdir(parents=True);shutil.copy2(icon,dest)
            if name!='codex': desktop(stage,name)
        else:
            src = source(p, work/'source')
            if p.get('patch') == 'addwater':
                replacements = {
                    'src/apps/firefox/firefox_paths.py': [('environ.get("HOST_XDG_CONFIG_HOME", expanduser("~/.config"))','environ.get("HOST_XDG_CONFIG_HOME", environ.get("XDG_CONFIG_HOME", expanduser("~/.config")))')],
                    'src/apps/firefox/firefox_details.py': [('cfg = ConfigParser()', 'cfg = ConfigParser(strict=False)')],
                    'src/preferences.py': [('["addwater", "--quick-update"]','["/usr/bin/addwater", "--quick-update"]')],
                }
                for path, changes in replacements.items():
                    f=src/path; text=f.read_text()
                    for old,new in changes:
                        if old not in text: raise ValueError('Patch no longer applies: '+path)
                        text=text.replace(old,new)
                    f.write_text(text)
            if kind == 'meson':
                meson_build(src,stage,p,name,suite,work,output)
                return
            elif kind == 'vpn':
                for f in ['app.py','backend.py','session.py','helper.py']:
                    write(stage,'usr/share/vpn-manager/'+f,(src/f).read_text())
                for f, dest in [('io.github.soltros.VPNManager.desktop','usr/share/applications/'),('io.github.soltros.VPNManager.svg','usr/share/icons/hicolor/scalable/apps/')]:
                    write(stage,dest+f,(src/f).read_text())
                launcher(stage,name,'/usr/bin/python3')
                write(stage,'usr/bin/vpn-manager','#!/bin/sh\nexec /usr/bin/python3 /usr/share/vpn-manager/app.py "$@"\n',0o755)
                write(stage,'usr/share/vpn-manager/vpn-manager-helper','#!/bin/sh\nexport PATH=/usr/sbin:/usr/bin:/sbin:/bin\nexec /usr/bin/python3 -I /usr/share/vpn-manager/helper.py\n',0o755)
                write(stage,'usr/share/doc/vpn-manager/copyright',(src/'LICENSE').read_text())
            elif kind == 'extension':
                dest = stage/'usr/share/gnome-shell/extensions/quick-settings-tray@soltros'
                copytree(src,dest)
                if (dest/'schemas').is_dir(): run('glib-compile-schemas','--strict',dest/'schemas')
            elif kind == 'dub':
                run('git','clone','--depth=1','--branch','v0.9.9','https://github.com/Kymorphia/gid.git',src/'gid')
                f=src/'dub.sdl';s=f.read_text();old='dependency "gid:adw1" version="~>0.9.9"'
                if old not in s: raise ValueError('Hideout dependency patch no longer applies')
                f.write_text(s.replace(old,'dependency "gid:adw1" path="gid"'))
                run('dub','build','--build=release','--compiler=ldc2',cwd=src)
                dest=stage/'usr/bin/hideout';dest.parent.mkdir(parents=True);shutil.copy2(src/'hideout',dest)
                for path,dest in [('hideout_icon.svg','usr/share/icons/hicolor/scalable/apps/it.andreafontana.hideout.svg'),('it.andreafontana.hideout.desktop','usr/share/applications/it.andreafontana.hideout.desktop'),('data/it.andreafontana.hideout.metainfo.xml','usr/share/metainfo/it.andreafontana.hideout.metainfo.xml')]:
                    write(stage,dest,(src/path).read_text())
            elif kind == 'npm':
                run('npm','ci',cwd=src)
                run('npx','--no-install','electron-builder','--linux','--dir',cwd=src)
                bundles=list((src/'dist').glob('*-unpacked'))
                if len(bundles)!=1: raise ValueError('Expected exactly one Electron bundle')
                copytree(bundles[0],stage/'opt'/name)
                candidates=[f for f in (stage/'opt'/name).iterdir() if f.is_file() and f.name.lower()=='vacuumtube']
                if len(candidates)!=1: raise ValueError('VacuumTube executable missing')
                launcher(stage,name,'/opt/'+name+'/'+candidates[0].name);desktop(stage,name)
            elif kind == 'xenia':
                build_xenia(src,stage)
            else:
                raise ValueError(p.get('reason','Unsupported build kind: '+kind))
            # Preserve upstream license files for all source-built packages.
            for f in list(src.glob('LICENSE*')) + list(src.glob('COPYING*')):
                if f.is_file(): write(stage,f'usr/share/doc/{name}/'+f.name,f.read_text(errors='replace'))
        filename=control(stage,name,p,arch,suite)
        epoch=int(os.environ.get('SOURCE_DATE_EPOCH','1794484800'))
        for f in stage.rglob('*'):
            if not f.is_symlink(): os.utime(f,(epoch,epoch))
        run('dpkg-deb','--root-owner-group','-Zxz','--build',stage,output/filename)


def patch_xenia_premake(src):
    # The bundled libzip predates modern compiler checks for implicit function
    # declarations. getpid() needs unistd.h on POSIX; io.h remains Windows-only.
    for name in ['mkstemp.c','zipint.h']:
        path=src/'third_party/premake-core/contrib/libzip'/name
        old='#include <io.h>\n#endif'
        new='#include <io.h>\n#else\n#include <unistd.h>\n#endif'
        text=path.read_text()
        if text.count(old)!=1:
            raise ValueError('Xenia Premake libzip header patch no longer applies: '+name)
        path.write_text(text.replace(old,new))


def build_xenia(src,stage):
    deps='xbyak imgui catch premake-core snappy premake-export-compile-commands discord-rpc rapidjson aes_128 capstone cpptoml cxxopts SDL2 utfcpp fmt disruptorplus premake-cmake date xxhash FFmpeg premake-androidndk FidelityFX-CAS FidelityFX-FSR Vulkan-Headers glslang SPIRV-Tools VulkanMemoryAllocator'.split()
    run('git','submodule','update','--init','--depth=1','--',*['third_party/'+d for d in deps],cwd=src)
    f=src/'premake5.lua';f.write_text(f.read_text().replace('"FatalWarnings",',''))
    patch_xenia_premake(src)
    # Build the exact bundled Premake used by upstream instead of a host version.
    run('make','-f','Bootstrap.mak','linux','-j2',cwd=src/'third_party/premake-core')
    premake=src/'third_party/premake-core/bin/release/premake5'
    run(premake,'--scripts=third_party/premake-core','--file=premake5.lua','--os=linux','--cc=clang','--test-suite-mode=combined','cmake',cwd=src)
    write(src,'build/version.h','#pragma once\n#define XE_BUILD_BRANCH "master"\n#define XE_BUILD_COMMIT "95a5c3ee250f80c3b9d139658649d9ffb6db3eec"\n#define XE_BUILD_COMMIT_SHORT "95a5c3e"\n#define XE_BUILD_DATE "2026-11-12"\n')
    env=dict(os.environ,CC='clang',CXX='clang++',CXXFLAGS='-include cstdint -Wno-error=unused-result -Wno-deprecated-literal-operator -Wno-integer-overflow')
    run('cmake','-S','build','-B','build/cmake-Release','-G','Ninja','-DCMAKE_BUILD_TYPE=Release',cwd=src,env=env)
    run('cmake','--build','build/cmake-Release','--parallel','2','--target','xenia-app',cwd=src,env=env)
    dest=stage/'usr/bin/xenia';dest.parent.mkdir(parents=True);shutil.copy2(src/'build/bin/Linux/Release/xenia',dest)
    desktop(stage,'xenia')


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('package',choices=PACKAGES)
    a.add_argument('--arch',default=subprocess.check_output(['dpkg','--print-architecture'],text=True).strip())
    a.add_argument('--suite',choices=['stonking'],default='stonking')
    a.add_argument('--output',type=Path,default=ROOT/'dist')
    a.add_argument('--allow-restricted',action='store_true')
    args=a.parse_args()
    build(args.package,args.arch,args.suite,args.output,args.allow_restricted)


if __name__=='__main__': main()
