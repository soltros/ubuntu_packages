import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_prune", ROOT / "scripts/prune-release-assets.py")
prune = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prune)


def record(name, version="2", arch="amd64"):
    return (
        f"Package: sample\nVersion: {version}\nArchitecture: {arch}\n"
        f"Filename: {name}\nSize: 8\nSHA256: {'a'*64}\n\n"
    )


class ReleasePruneTests(unittest.TestCase):
    def test_index_parsing(self):
        self.assertEqual(
            prune.indexed_debs(record("sample_2_amd64.deb") + record("other_1_all.deb")),
            {"sample_2_amd64.deb", "other_1_all.deb"},
        )

    def test_empty_or_malformed_index_is_rejected(self):
        for value in (
            "",
            "Package: sample\nVersion: 2\nArchitecture: amd64\n",
            record("../unsafe.deb"),
            record("same.deb") + record("same.deb"),
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    prune.indexed_debs(value)

    def test_only_stale_debs_are_deleted(self):
        assets = [
            {"id": 1, "name": "sample_1_amd64.deb"},
            {"id": 2, "name": "sample_2_amd64.deb"},
            {"id": 3, "name": "InRelease"},
            {"id": 4, "name": "Packages"},
            {"id": 5, "name": "soltros-archive-keyring.asc"},
            {"id": 6, "name": "README.txt"},
        ]
        self.assertEqual(prune.obsolete_asset_ids(assets, {"sample_2_amd64.deb"}), [(1, "sample_1_amd64.deb")])

    def test_never_delete_if_indexed_deb_is_missing(self):
        with self.assertRaisesRegex(ValueError, "missing indexed"):
            prune.obsolete_asset_ids(
                [{"id": 1, "name": "old.deb"}],
                {"current.deb"},
            )

    def test_duplicate_release_asset_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate GitHub asset"):
            prune.obsolete_asset_ids(
                [{"id": 1, "name": "same.deb"}, {"id": 2, "name": "same.deb"}],
                {"same.deb"},
            )


if __name__ == "__main__":
    unittest.main()
