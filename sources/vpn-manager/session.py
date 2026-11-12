"""One authenticated, private helper session per application launch."""
import json
import os
from pathlib import Path
import selectors
import subprocess
from backend import Profile, State, VPNError


class Session:
    def __init__(self):
        self.process = None

    @property
    def authorized(self):
        return self.process is not None and self.process.poll() is None

    def start(self):
        if self.authorized:
            return
        pkexec = '/run/wrappers/bin/pkexec' if Path('/run/wrappers/bin/pkexec').exists() else 'pkexec'
        helper = str(Path(__file__).resolve().parent / 'vpn-manager-helper')
        try:
            self.process = subprocess.Popen([pkexec, '--disable-internal-agent', helper],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1)
            response = self.read(180)
            if response != {'ready': True}:
                raise VPNError('Administrator authentication was not completed.')
        except (OSError, VPNError) as error:
            self.close()
            raise VPNError('Administrator authentication was cancelled or unavailable. Click Refresh to try again.') from error

    def read(self, timeout):
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout):
                raise VPNError('The administrator helper did not respond in time.')
        line = self.process.stdout.readline()
        if not line:
            raise VPNError('The administrator session ended. Reopen VPN Manager to authenticate again.')
        try:
            return json.loads(line)
        except ValueError as error:
            raise VPNError('The administrator helper returned an invalid response.') from error

    def request(self, operation, **arguments):
        if not self.authorized:
            raise VPNError('Administrator authentication is required. Click Refresh to try again.')
        try:
            self.process.stdin.write(json.dumps({'operation': operation, **arguments}) + '\n')
            self.process.stdin.flush()
            response = self.read(180)
        except (OSError, VPNError) as error:
            self.close()
            raise VPNError('The administrator session ended. Click Refresh to authenticate again.') from error
        if 'error' in response:
            raise VPNError(response['error'])
        return response.get('result')

    def status(self):
        if not self.authorized:
            return State(errors=['Administrator authentication is required. Click Refresh to try again.'])
        try:
            data = self.request('status')
            data['profiles'] = [Profile(**profile) for profile in data['profiles']]
            return State(**data)
        except VPNError as error:
            return State(errors=[str(error)])

    def switch(self, target):
        self.request('switch', target=target)

    def disconnect(self, target):
        self.request('disconnect', target=target)

    def remove(self, uuid):
        self.request('remove', target=uuid)

    def import_config(self, path):
        # Read as the desktop user: the privileged process never opens arbitrary
        # user-supplied paths, symlinks, or root-only files.
        try:
            with open(path, encoding='utf-8') as source:
                content = source.read(1024 * 1024 + 1)
        except (OSError, UnicodeError) as error:
            raise VPNError('Cannot read that configuration file.') from error
        if len(content) > 1024 * 1024:
            raise VPNError('The configuration is too large.')
        self.request('import', name=Path(path).stem, content=content)

    def close(self):
        process, self.process = self.process, None
        if process:
            # EOF ends the root helper; do not require the user process to signal root.
            if process.stdin:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            if process.stdout:
                process.stdout.close()
