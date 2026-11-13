import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('silo_build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class SiloTests(unittest.TestCase):
    def test_native_release_installs_browser_metadata_and_extension_host_without_user_installer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stage, bundle = root / 'stage', root / 'bundle'
            bundle.mkdir()
            shutil.copy2('/bin/true', bundle / 'silo')
            resources = {
                'data/com.nofaff.Silo.desktop': '[Desktop Entry]\nName=Silo\nExec=silo %u\nType=Application\nMimeType=x-scheme-handler/http;x-scheme-handler/https;\n',
                'data/icons/hicolor/128x128/apps/com.nofaff.Silo.png': 'icon',
                'LICENSE': 'MIT', 'README.md': 'Silo',
                'native-host/silo-host.py': '#!/usr/bin/env python3\n',
                'native-host/com.nofaff.silo.firefox.json': json.dumps({'name':'com.nofaff.silo','path':'SILO_HOST_PATH','type':'stdio','allowed_extensions':['silo@nofaff.dev']}),
                'install.sh': '#!/bin/sh\nexit 99\n',
                'uninstall.sh': '#!/bin/sh\nexit 99\n',
            }
            for path, content in resources.items():
                file = bundle / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content)
            with patch.object(build.subprocess, 'run', side_effect=AssertionError('User installer must not execute')):
                build.install_silo(stage, bundle)
            self.assertEqual((stage / 'usr/bin/silo').read_bytes()[:4], b'\x7fELF')
            desktop = (stage / 'usr/share/applications/com.nofaff.Silo.desktop').read_text()
            self.assertIn('x-scheme-handler/https;', desktop)
            host = json.loads((stage / 'usr/lib/mozilla/native-messaging-hosts/com.nofaff.silo.json').read_text())
            self.assertEqual(host['path'], '/usr/lib/silo/silo-host.py')
            self.assertEqual(host['allowed_extensions'], ['silo@nofaff.dev'])
            self.assertFalse(bundle.exists())
            self.assertFalse(list(stage.rglob('install.sh')))
            self.assertFalse((stage / 'DEBIAN/postinst').exists())

    def test_manifest_tracks_stable_upstream_and_pins_native_archive(self):
        p = build.PACKAGES['silo']
        self.assertEqual(p['track'], {'kind':'release','repo':'no-faff/Silo','prefix':'v'})
        self.assertTrue(p['downloads']['amd64']['url'].endswith('.tar.gz'))
        self.assertIn('libadwaita-1-0', p['depends'])
