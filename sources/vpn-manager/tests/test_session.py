import io
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from backend import Profile, State, VPNError
from helper import dispatch, serve
from session import Session


class AuthenticationTests(unittest.TestCase):
    def test_launch_authenticates_once(self):
        process = Mock()
        process.poll.return_value = None
        session = Session()
        with patch('session.subprocess.Popen', return_value=process) as popen, \
             patch('session.Path.exists', return_value=True), \
             patch.object(session, 'read', return_value={'ready': True}):
            session.start()
            session.start()
        popen.assert_called_once()
        args = popen.call_args.args[0]
        self.assertEqual(args[:2], ['/run/wrappers/bin/pkexec', '--disable-internal-agent'])
        self.assertTrue(args[2].endswith('/vpn-manager-helper'))
        self.assertTrue(session.authorized)

    def test_cancel_leaves_controls_locked(self):
        process = Mock()
        session = Session()
        with patch('session.subprocess.Popen', return_value=process), \
             patch.object(session, 'read', side_effect=VPNError('cancelled')):
            with self.assertRaises(VPNError):
                session.start()
        self.assertFalse(session.authorized)
        self.assertTrue(session.status().errors)
        process.stdin.close.assert_called_once()

    def test_unauthenticated_operation_never_launches_command(self):
        with patch('session.subprocess.Popen') as popen:
            with self.assertRaises(VPNError):
                Session().switch('tailscale')
        popen.assert_not_called()

    def test_close_ends_pipe_session(self):
        session = Session()
        process = session.process = Mock()
        session.close()
        process.stdin.close.assert_called_once()
        self.assertFalse(session.authorized)

    def test_does_not_send_arbitrary_paths_to_root(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'provider.conf'
            path.write_text('[Interface]\n[Peer]\n')
            session = Session()
            with patch.object(session, 'request') as request:
                session.import_config(str(path))
            self.assertEqual(request.call_args.kwargs, {'name': 'provider', 'content': '[Interface]\n[Peer]\n'})


class HelperTests(unittest.TestCase):
    def test_arbitrary_commands_rejected(self):
        with self.assertRaises(VPNError):
            dispatch(Mock(), {'operation': 'execute', 'command': 'sh'})

    def test_non_wireguard_targets_rejected(self):
        backend = Mock()
        backend.status.return_value = State('Stopped', profiles=[])
        for operation in ['switch', 'disconnect', 'remove']:
            with self.assertRaises(VPNError):
                dispatch(backend, {'operation': operation, 'target': 'ethernet-uuid'})
        backend.remove.assert_not_called()
        backend.disconnect.assert_not_called()
        backend.switch.assert_not_called()

    def test_private_temp_config_and_sanitized_name(self):
        backend = Mock()
        def check(path):
            self.assertEqual(Path(path).name, '---provider.conf')
            self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(path).read_text(), 'content')
            return 'uuid'
        backend.import_config.side_effect = check
        self.assertEqual(dispatch(backend, {'operation': 'import', 'name': '../provider', 'content': 'content'}), 'uuid')

    def test_helper_handles_multiple_requests_until_eof(self):
        backend = Mock()
        backend.status.return_value = State('Stopped')
        source = io.StringIO('{"operation":"status"}\n{"operation":"status"}\n')
        destination = io.StringIO()
        with tempfile.TemporaryFile() as lock:
            serve(backend, source, destination, lock)
        self.assertEqual(len(destination.getvalue().splitlines()), 3)
        self.assertEqual(backend.status.call_count, 2)
