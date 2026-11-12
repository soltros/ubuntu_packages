import tempfile
import unittest
import subprocess
from unittest.mock import patch
from pathlib import Path
from backend import Backend, Profile, State, VPNError, fields, command


class SwitchingTests(unittest.TestCase):
    def backend(self, states, fail=None):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if fail and fail in args:
                raise VPNError('Denied')
            return ''
        backend = Backend(run, sleep=lambda _: None, attempts=1)
        iterator = iter(states)
        backend.status = lambda: next(iterator)
        return backend, calls

    def test_disconnect_tailscale_before_wireguard(self):
        profile = Profile('wg-uuid', 'Provider')
        backend, calls = self.backend([State('Running', profiles=[profile]), State('Stopped', profiles=[profile]), State('Stopped', profiles=[Profile(profile.uuid, profile.name, 'wg0', True)])])
        backend.switch(profile.uuid)
        self.assertEqual(calls[0], ['tailscale', 'down'])
        self.assertEqual(calls[-1], ['nmcli', '--wait', '30', 'connection', 'up', 'uuid', profile.uuid])

    def test_disconnect_wireguard_before_tailscale(self):
        backend, calls = self.backend([State('Stopped', profiles=[Profile('wg', 'Provider', 'wg0', True)]), State('Stopped'), State('Running')])
        backend.switch('tailscale')
        self.assertIn('down', calls[-2])
        self.assertEqual(calls[-1], ['tailscale', 'up'])

    def test_wireguard_always_explicitly_stops_tailscale(self):
        profile = Profile('wg', 'Provider')
        state = State('Stopped', profiles=[profile])
        backend, calls = self.backend([state, state, state])
        backend.switch('wg')
        self.assertEqual(calls[0], ['tailscale', 'down'])

    def test_starting_tailscale_blocks_wireguard(self):
        profile = Profile('wg', 'Provider')
        backend, calls = self.backend([State('Running', profiles=[profile]), State('Starting', profiles=[profile])])
        with self.assertRaises(VPNError):
            backend.switch('wg')
        self.assertFalse(any('up' in call for call in calls))

    def test_waits_for_shutdown(self):
        profile = Profile('wg', 'Provider')
        backend, calls = self.backend([State('Running', profiles=[profile]),
            State('Running', profiles=[profile]), State('Stopped', profiles=[profile]),
            State('Stopped', profiles=[profile])])
        backend.attempts = 2
        backend.switch('wg')
        self.assertEqual(calls[-1][-3:], ['up', 'uuid', 'wg'])

    def test_wireguard_shutdown_failure_blocks_tailscale(self):
        state = State('Stopped', profiles=[Profile('wg', 'Provider', 'wg0', True)])
        backend, calls = self.backend([state], fail='down')
        with self.assertRaises(VPNError):
            backend.switch('tailscale')
        self.assertNotIn(['tailscale', 'up'], calls)

    def test_wireguard_still_present_blocks_tailscale(self):
        state = State('Stopped', profiles=[Profile('wg', 'Provider', 'wg0', True)])
        backend, calls = self.backend([state, state])
        with self.assertRaises(VPNError):
            backend.switch('tailscale')
        self.assertNotIn(['tailscale', 'up'], calls)

    def test_tailscale_reappears_after_wireguard_activation(self):
        profile = Profile('wg', 'Provider')
        backend, calls = self.backend([State('Running', profiles=[profile]),
            State('Stopped', profiles=[profile]), State('Running', profiles=[Profile('wg', 'Provider', 'wg0', True)])])
        with self.assertRaises(VPNError):
            backend.switch('wg')
        self.assertEqual(calls[-1], ['nmcli', '--wait', '30', 'connection', 'down', 'uuid', 'wg'])

    def test_wireguard_reappears_after_tailscale_activation(self):
        backend, calls = self.backend([State('Stopped'), State('Stopped'),
            State('Running', profiles=[Profile('wg', 'Provider', 'wg0', True)])])
        with self.assertRaises(VPNError):
            backend.switch('tailscale')
        self.assertEqual(calls[-1], ['tailscale', 'down'])

    def test_failed_disconnect_never_connects(self):
        backend, calls = self.backend([State('Running', profiles=[Profile('wg', 'Provider')])], fail='down')
        with self.assertRaises(VPNError):
            backend.switch('wg')
        self.assertFalse(any('up' in c for c in calls))

    def test_still_running_never_connects(self):
        state = State('Running', profiles=[Profile('wg', 'Provider')])
        backend, calls = self.backend([state, state])
        with self.assertRaises(VPNError):
            backend.switch('wg')
        self.assertFalse(any('up' in c for c in calls))

    def test_external_and_unknown_block_mutations(self):
        for state in [State('Stopped', external=['wg0']), State(errors=['unavailable'])]:
            backend, calls = self.backend([state])
            with self.assertRaises(VPNError):
                backend.switch('tailscale')
            self.assertEqual(calls, [])

    def test_missing_profile_leaves_connection_untouched(self):
        backend, calls = self.backend([State('Running')])
        with self.assertRaises(VPNError):
            backend.switch('missing')
        self.assertEqual(calls, [])

    def test_import_disables_autoconnect(self):
        calls = []
        uuid = '12345678-1234-1234-1234-123456789abc'
        def run(args, **kwargs):
            calls.append(args)
            return f"Connection 'provider' ({uuid}) successfully added."
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'provider.conf'
            path.write_text('[Interface]\nPrivateKey = secret\n[Peer]\nPublicKey = public\n')
            self.assertEqual(Backend(run).import_config(str(path)), uuid)
        self.assertIn('--temporary', calls[0])
        self.assertEqual(calls[-1][-2:], ['connection.autoconnect', 'no'])
        self.assertFalse(any('up' in c for c in calls))

    def test_hooks_rejected_without_commands(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'provider.conf'
            path.write_text('[Interface]\nPostUp = touch /tmp/unsafe\n[Peer]\n')
            with self.assertRaises(VPNError):
                Backend(lambda args, **kwargs: calls.append(args)).import_config(str(path))
        self.assertEqual(calls, [])

    def test_colon_in_profile_name(self):
        self.assertEqual(fields(r'uuid:VPN\: London:wireguard:wg0'), ['uuid', 'VPN: London', 'wireguard', 'wg0'])

    def test_escaped_backslash_before_separator(self):
        self.assertEqual(fields(r'uuid:VPN\\:wireguard:wg0'), ['uuid', 'VPN\\', 'wireguard', 'wg0'])

    def test_empty_ip_link_placeholders(self):
        outputs = iter(['{"BackendState":"Running"}', '', '', '[{},{},{}]'])
        state = Backend(lambda args: next(outputs)).status()
        self.assertEqual(state.errors, [])
        self.assertEqual(state.external, [])

    def test_login_required_does_not_disconnect_wireguard(self):
        backend, calls = self.backend([State('NeedsLogin', profiles=[Profile('wg', 'Provider', 'wg0', True)])])
        with self.assertRaises(VPNError):
            backend.switch('tailscale')
        self.assertEqual(calls, [])

    def test_detects_external_interface(self):
        outputs = iter(['{"BackendState":"Stopped"}', 'id:Home:wireguard:wg0', 'id',
                        '[{"ifname":"wg0"},{"ifname":"wg-other"}]'])
        state = Backend(lambda args: next(outputs)).status()
        self.assertEqual(state.external, ['wg-other'])
        self.assertTrue(state.profiles[0].active)


if __name__ == '__main__':
    unittest.main()
