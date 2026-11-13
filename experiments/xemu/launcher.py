#!/usr/bin/env python3
"""Launch the optimized xemu in an isolated configuration/cache directory."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tomllib


def set_option(text, section, key, value):
    # Edit one scalar without serializing/reformatting the rest of xemu's TOML.
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip() == f'[{section}]'), None)
    if start is None:
        result = text.rstrip() + f'\n\n[{section}]\n{key} = {value}\n'
    else:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
        body = [line for line in lines[start + 1:end] if not re.match(r'\s*' + re.escape(key) + r'\s*=', line)]
        if body and not body[-1].endswith('\n'):
            body[-1] += '\n'
        result = ''.join(lines[:start + 1] + body + [f'{key} = {value}\n'] + lines[end:])
    tomllib.loads(result)  # Refuse an invalid edit before replacing any user config.
    return result


def prepare(home, env, args):
    standard = Path(env.get('XDG_DATA_HOME') or home / '.local/share') / 'xemu/xemu'
    isolated = Path(env.get('XDG_DATA_HOME') or home / '.local/share') / 'xemu-perf'
    base = isolated / 'xemu/xemu'
    base.mkdir(parents=True, exist_ok=True)
    config = base / 'xemu.toml'
    if not config.exists():
        if (standard / 'xemu.toml').is_file():
            shutil.copy2(standard / 'xemu.toml', config)
        else:
            config.write_text('')
        for filename in ['eeprom.bin']:
            if (standard / filename).is_file():
                shutil.copy2(standard / filename, base / filename)
    original = config.read_text()
    text = original
    edits = [('display', 'renderer', json.dumps(args.renderer)), ('perf', 'cache_shaders', str(not args.no_disk_cache).lower())]
    if args.workers is not None:
        edits.append(('audio.vp', 'num_workers', str(args.workers)))
    if args.dsp_jit or args.interpreter:
        edits.append(('audio', 'use_dsp_jit', str(args.dsp_jit).lower()))
    for section, key, value in edits:
        text = set_option(text, section, key, value)
    if text != original:
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        shutil.copy2(config, config.with_suffix('.toml.' + stamp + '.bak'))
        temp = config.with_suffix('.tmp')
        temp.write_text(text)
        temp.replace(config)
    result = dict(env, XDG_DATA_HOME=str(isolated))
    return config, result


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workers', type=int, choices=range(0, 17), help='Audio voice workers; 0 is upstream auto. Try 4 vs 0 on the Ryzen desktop.')
    group = p.add_mutually_exclusive_group()
    group.add_argument('--dsp-jit', action='store_true', help='Opt into the existing upstream DSP JIT; test audio accuracy.')
    group.add_argument('--interpreter', action='store_true', help='Return to the upstream default DSP interpreter.')
    p.add_argument('--renderer', choices=['VULKAN', 'OPENGL'], default='VULKAN')
    p.add_argument('--no-disk-cache', action='store_true', help='Disable persistent caches for a comparison run.')
    p.add_argument('--baseline', action='store_true', help='Use stable /usr/bin/xemu with the same experimental settings.')
    p.add_argument('xemu_args', nargs=argparse.REMAINDER)
    return p.parse_args(argv)


def main():
    args = parse_args()
    config, env = prepare(Path.home(), os.environ, args)
    binary = '/usr/bin/xemu' if args.baseline else '/usr/lib/xemu-perf/xemu'
    if not Path(binary).is_file():
        raise SystemExit(f'Missing {binary}; install the corresponding package first.')
    extra = args.xemu_args
    if extra[:1] == ['--']:
        extra = extra[1:]
    if '-config_path' in extra:
        raise SystemExit('Use the managed experimental config; -config_path is not accepted.')
    print(f'XEMU (Optimizations): {binary}; config {config}', file=sys.stderr, flush=True)
    os.execve(binary, [binary, '-config_path', str(config), *extra], env)


if __name__ == '__main__':
    main()
