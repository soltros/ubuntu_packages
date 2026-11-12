"""Network operations, kept separate from GTK for deterministic safety tests."""
import json
import os
import re
import time
import subprocess
from dataclasses import dataclass, field


class VPNError(Exception):
    pass


def command(args, privileged=False):
    env = dict(os.environ, LC_ALL='C')
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=60, env=env)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise VPNError(f'{args[0]} could not complete. Check that its service is available.') from error
    if result.returncode:
        # Never show command output: imported configurations can contain secrets.
        raise VPNError(f'{args[0]} could not complete the request. Check service availability and permissions.')
    return result.stdout


def fields(line):
    parts, current, escaped = [], [], False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ':':
            parts.append(''.join(current))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    return parts + [''.join(current)]


@dataclass
class Profile:
    uuid: str
    name: str
    device: str = ''
    active: bool = False


@dataclass
class State:
    tailscale: str = 'Unknown'
    address: str = ''
    profiles: list = field(default_factory=list)
    external: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def ts_active(self):
        return self.tailscale in ('Running', 'Starting')


class Backend:
    def __init__(self, run=command, sleep=time.sleep, attempts=20):
        self.run = run
        self.sleep = sleep
        self.attempts = attempts

    def status(self):
        state = State()
        try:
            data = json.loads(self.run(['tailscale', 'status', '--json']))
            state.tailscale = data.get('BackendState', 'Unknown')
            state.address = ', '.join(data.get('TailscaleIPs', []))
            if state.tailscale not in ('Running', 'Starting', 'Stopped', 'NeedsLogin', 'NeedsMachineAuth'):
                state.errors.append('Tailscale status is unavailable.')
        except (VPNError, ValueError, AttributeError, TypeError):
            state.errors.append('Cannot read Tailscale. Make sure tailscaled is running.')
        try:
            rows = self.run(['nmcli', '-t', '-f', 'UUID,NAME,TYPE,DEVICE', 'connection', 'show'])
            active = set(self.run(['nmcli', '-t', '-f', 'UUID', 'connection', 'show', '--active']).splitlines())
            for row in rows.splitlines():
                uuid, name, kind, device = fields(row)
                if kind == 'wireguard':
                    state.profiles.append(Profile(uuid, name, device, uuid in active))
            links = json.loads(self.run(['ip', '-j', 'link', 'show', 'type', 'wireguard']))
            managed = {p.device for p in state.profiles if p.active}
            state.external = [link['ifname'] for link in links if link and link['ifname'] not in managed]
        except (VPNError, ValueError, KeyError, TypeError):
            state.errors.append('Cannot read WireGuard. Make sure NetworkManager is running.')
        return state

    def switch(self, target):
        before = self.status()
        if before.errors:
            raise VPNError('Connection state is unknown. Restore service access before switching.')
        if before.external:
            raise VPNError('WireGuard is managed outside NetworkManager: ' + ', '.join(before.external)
                           + '. Stop it with the tool that started it before switching.')
        if target == 'tailscale' and before.tailscale in ('NeedsLogin', 'NeedsMachineAuth'):
            raise VPNError('Sign in to Tailscale first using its setup, then return here.')
        if target != 'tailscale' and not any(p.uuid == target for p in before.profiles):
            raise VPNError('This profile no longer exists. Refresh the list.')
        if target != 'tailscale':
            self.run(['tailscale', 'down'], privileged=True)
        for profile in before.profiles:
            if profile.active and profile.uuid != target:
                self.disconnect(profile.uuid)
        # Wait for asynchronous shutdown, checking all relevant services each time.
        current = None
        for _ in range(self.attempts):
            current = self.status()
            if current.errors or current.external:
                raise VPNError('The previous connection could not be verified. Nothing else was started.')
            stopped = (target == 'tailscale' or current.tailscale == 'Stopped') and not any(
                p.active and p.uuid != target for p in current.profiles)
            if stopped:
                break
            self.sleep(0.25)
        else:
            raise VPNError('The previous connection is still active. Nothing else was started.')
        if target == 'tailscale':
            if current.tailscale in ('NeedsLogin', 'NeedsMachineAuth'):
                raise VPNError('Sign in to Tailscale first using its setup, then return here.')
            self.run(['tailscale', 'up'], privileged=True)
        else:
            self.run(['nmcli', 'connection', 'modify', 'uuid', target, 'connection.autoconnect', 'no'], privileged=True)
            self.run(['nmcli', '--wait', '30', 'connection', 'up', 'uuid', target], privileged=True)

        # A competing tool may reconnect the other VPN during activation. Stop the
        # newly requested connection if exclusivity cannot be confirmed afterward.
        after = self.status()
        conflict = after.errors or after.external or (
            target != 'tailscale' and after.tailscale != 'Stopped') or any(
                p.active and p.uuid != target for p in after.profiles)
        if conflict:
            self.disconnect(target)
            raise VPNError('Another connection appeared during the switch. The new connection was stopped.')

    def disconnect(self, target):
        if target == 'tailscale':
            self.run(['tailscale', 'down'], privileged=True)
        else:
            self.run(['nmcli', 'connection', 'modify', 'uuid', target, 'connection.autoconnect', 'no'], privileged=True)
            self.run(['nmcli', '--wait', '30', 'connection', 'down', 'uuid', target], privileged=True)

    def import_config(self, path):
        # Hooks are not supported by NetworkManager; refuse rather than silently
        # dropping kill-switch or routing behavior. Never execute imported scripts.
        try:
            with open(path, encoding='utf-8') as source:
                content = source.read(1024 * 1024 + 1)
        except (OSError, UnicodeError) as error:
            raise VPNError('Cannot read that configuration file.') from error
        if len(content) > 1024 * 1024 or '[Interface]' not in content or '[Peer]' not in content:
            raise VPNError('Choose a WireGuard configuration containing Interface and Peer sections.')
        if re.search(r'^\s*(PreUp|PostUp|PreDown|PostDown|SaveConfig)\s*=', content, re.M | re.I):
            raise VPNError('This config contains wg-quick hooks or SaveConfig, which NetworkManager cannot preserve. Import a plain provider config instead.')
        output = self.run(['nmcli', 'connection', 'import', '--temporary', 'type', 'wireguard', 'file', path], privileged=True)
        match = re.search(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b', output, re.I)
        if not match:
            raise VPNError('Import returned an unexpected result. Refresh before trying again.')
        uuid = match.group()
        try:
            self.run(['nmcli', 'connection', 'modify', 'uuid', uuid, 'connection.autoconnect', 'no'], privileged=True)
        except VPNError:
            self.run(['nmcli', 'connection', 'delete', 'uuid', uuid], privileged=True)
            raise
        return uuid

    def remove(self, uuid):
        self.run(['nmcli', 'connection', 'delete', 'uuid', uuid], privileged=True)
