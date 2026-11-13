import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'experiments/xemu'


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = load('perf_launcher', 'launcher.py')
merger = load('perf_merger', 'merge_repo.py')
build = load('perf_builder', 'build.py')


def package(root, name, version):
    stage = root / (name + version)
    (stage / 'DEBIAN').mkdir(parents=True)
    (stage / 'DEBIAN/control').write_text(f'Package: {name}\nVersion: {version}\nArchitecture: amd64\nMaintainer: Test <test@example.org>\nDescription: test\n')
    deb = root / f'{name}_{version}_amd64.deb'
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(deb)], check=True, stdout=subprocess.DEVNULL)
    return deb, stage


class PerfTests(unittest.TestCase):
    def test_launcher_isolates_sdl_data_and_keeps_stable_config(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            standard = home / '.local/share/xemu/xemu'
            standard.mkdir(parents=True)
            original = '# user setting\n[audio]\nuse_dsp_jit = false\n[display]\nrenderer = "OPENGL"\n[machine]\nhdd_path="/games/xbox.qcow2"\n'
            (standard / 'xemu.toml').write_text(original)
            (standard / 'eeprom.bin').write_bytes(b'EEPROM')
            args = launcher.parse_args(['--workers', '4', '--dsp-jit'])
            path, env = launcher.prepare(home, {}, args)
            actual = tomllib.loads(path.read_text())
            self.assertEqual(actual['audio']['vp']['num_workers'], 4)
            self.assertTrue(actual['audio']['use_dsp_jit'])
            self.assertEqual(actual['machine']['hdd_path'], '/games/xbox.qcow2')
            self.assertEqual((standard / 'xemu.toml').read_text(), original)
            self.assertEqual(path.parent / 'eeprom.bin', path.with_name('eeprom.bin'))
            self.assertEqual(path.with_name('eeprom.bin').read_bytes(), b'EEPROM')
            self.assertEqual(Path(env['XDG_DATA_HOME']) / 'xemu/xemu/xemu.toml', path)
            path2, _ = launcher.prepare(home, {}, launcher.parse_args(['--workers', '0', '--interpreter']))
            again = tomllib.loads(path2.read_text())
            self.assertFalse(again['audio']['use_dsp_jit'])
            self.assertEqual(again['audio']['vp']['num_workers'], 0)

    def test_partial_publish_preserves_stable_and_full_publish_preserves_perf(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo, incoming = root / 'repo', root / 'incoming'
            repo.mkdir(); incoming.mkdir()
            stable, _ = package(repo, 'xemu', '1')
            before = stable.read_bytes()
            package(incoming, 'xemu-perf', '1')
            merger.merge(repo, incoming, 'xemu-perf')
            self.assertEqual(stable.read_bytes(), before)
            shutil.rmtree(incoming); incoming.mkdir()
            package(incoming, 'xemu', '2')
            merger.merge(repo, incoming, 'full')
            self.assertTrue((repo / 'xemu-perf_1_amd64.deb').is_file())
            self.assertFalse((repo / 'xemu_1_amd64.deb').exists())
            self.assertTrue((repo / 'xemu_2_amd64.deb').is_file())

    def test_partial_publish_rejects_other_packages_and_downgrades(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo, incoming = root / 'repo', root / 'incoming'
            repo.mkdir(); incoming.mkdir()
            package(repo, 'xemu-perf', '2')
            package(incoming, 'xemu', '9')
            with self.assertRaises(ValueError): merger.merge(repo, incoming, 'xemu-perf')
            shutil.rmtree(incoming); incoming.mkdir()
            package(incoming, 'xemu-perf', '1')
            with self.assertRaisesRegex(ValueError, 'downgrade'): merger.merge(repo, incoming, 'xemu-perf')

    def test_repack_has_native_binary_correct_menu_name_and_no_stable_file_collisions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            upstream, stage = package(root, 'xemu', '1')
            for directory in ['usr/bin', 'usr/share/applications', 'usr/share/doc/xemu', 'usr/share/icons/hicolor/scalable/apps']:
                (stage / directory).mkdir(parents=True)
            shutil.copy2('/bin/true', stage / 'usr/bin/xemu')
            (stage / 'usr/share/applications/xemu.desktop').write_text('Name=xemu\n')
            (stage / 'usr/share/icons/hicolor/scalable/apps/xemu.svg').write_text('<svg/>')
            subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(upstream)], check=True, stdout=subprocess.DEVNULL)
            result = build.repackage(upstream, root / 'out', '1-1soltrosperf1~stonking')
            extracted = root / 'extracted'
            subprocess.run(['dpkg-deb', '-x', str(result), str(extracted)], check=True)
            self.assertTrue((extracted / 'usr/lib/xemu-perf/xemu').read_bytes().startswith(b'\x7fELF'))
            self.assertIn('Name=XEMU (Optimizations)', (extracted / 'usr/share/applications/xemu-perf.desktop').read_text())
            self.assertTrue((extracted / 'usr/share/icons/hicolor/scalable/apps/xemu-perf.svg').exists())
            self.assertFalse((extracted / 'usr/bin/xemu').exists())
            self.assertIn('python3', subprocess.check_output(['dpkg-deb', '-f', str(result), 'Depends'], text=True))


if __name__ == '__main__':
    unittest.main()
