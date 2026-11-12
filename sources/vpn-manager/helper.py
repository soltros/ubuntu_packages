#!/usr/bin/env python3
"""Root helper: only typed VPN operations over inherited private pipes."""
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from dataclasses import asdict

# The installed directory is immutable in Nix and root-owned in the DEB.
# Python runs with -I to ignore user Python paths and startup customization.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend import Backend, VPNError


def dispatch(backend, request):
    if not isinstance(request, dict):
        raise VPNError('Invalid request.')
    operation = request.get('operation')
    if operation == 'status':
        return asdict(backend.status())
    if operation == 'import':
        content, name = request.get('content'), request.get('name')
        if not isinstance(content, str) or len(content) > 1024 * 1024 or not isinstance(name, str):
            raise VPNError('Invalid configuration.')
        name = re.sub(r'[^a-zA-Z0-9_-]', '-', name)[:40] or 'wireguard'
        with tempfile.TemporaryDirectory(prefix='vpn-manager-') as directory:
            path = Path(directory) / (name + '.conf')
            path.write_text(content)
            path.chmod(0o600)
            return backend.import_config(str(path))
    if operation not in ('switch', 'disconnect', 'remove'):
        raise VPNError('Unsupported operation.')
    target = request.get('target')
    if not isinstance(target, str):
        raise VPNError('Invalid connection.')
    if target == 'tailscale' and operation != 'remove':
        return getattr(backend, operation)(target)
    # Do not let a forged request disable/delete Wi-Fi or Ethernet profiles.
    state = backend.status()
    if state.errors or not any(p.uuid == target for p in state.profiles):
        raise VPNError('The WireGuard profile could not be verified.')
    return getattr(backend, operation)(target)


def serve(backend, source, destination, lock):
    destination.write(json.dumps({'ready': True}) + '\n')
    destination.flush()
    while True:
        line = source.readline(7 * 1024 * 1024)
        if not line:
            return
        if not line.endswith('\n'):
            return
        try:
            request = json.loads(line)
            # Serialize operations across separately launched copies as well.
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                result = dispatch(backend, request)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
            response = {'result': result}
        except VPNError as error:
            response = {'error': str(error)}
        except Exception:
            response = {'error': 'The VPN operation could not complete.'}
        destination.write(json.dumps(response) + '\n')
        destination.flush()


def main():
    if os.geteuid() != 0:
        return 1
    os.umask(0o077)
    # /run is root-owned; refuse symlinks for the process-wide operation lock.
    fd = os.open('/run/vpn-manager.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        serve(Backend(), sys.stdin, sys.stdout, lock)
    return 0


if __name__ == '__main__':
    sys.exit(main())
