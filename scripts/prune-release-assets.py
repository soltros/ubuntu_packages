#!/usr/bin/env python3
"""Prune GitHub Release DEBs absent from a successfully published APT Packages index.

Run only after the new InRelease and Packages assets have been uploaded.
Never delete index-referenced packages or non-DEB release assets.
"""
import argparse
import json
from pathlib import Path
import subprocess


def indexed_debs(index):
    names = set()
    for stanza in index.split("\n\n"):
        fields = {}
        for line in stanza.splitlines():
            if line and not line[0].isspace() and ": " in line:
                key, value = line.split(": ", 1)
                fields[key] = value
        if not fields:
            continue
        filename = fields.get("Filename", "")
        if not filename.endswith(".deb") or Path(filename).name != filename or filename in names:
            raise ValueError("Unsafe or duplicate package filename in Packages: " + repr(filename))
        if not all(k in fields for k in ("Package", "Version", "Architecture", "SHA256")):
            raise ValueError("Incomplete Packages stanza for " + filename)
        names.add(filename)
    if not names:
        raise ValueError("Refusing to prune against an empty Packages index")
    return names


def obsolete_asset_ids(assets, required):
    available = {a["name"] for a in assets}
    missing = required - available
    if missing:
        raise ValueError("Published release is missing indexed DEBs: " + ", ".join(sorted(missing)))
    seen = set()
    obsolete = []
    for asset in assets:
        name = asset["name"]
        if name in seen:
            raise ValueError("Duplicate GitHub asset name: " + name)
        seen.add(name)
        if name.endswith(".deb") and name not in required:
            obsolete.append((asset["id"], name))
    return obsolete


def gh_json(*args):
    return json.loads(subprocess.check_output(["gh", "api", *args], text=True))


def prune(repo, suite, directory):
    if suite not in ("resolute", "stonking"):
        raise ValueError("Unrecognized Ubuntu suite")
    expected = indexed_debs((directory / "Packages").read_text())
    # The generated index must describe exactly the local DEBs being uploaded.
    local = {path.name for path in directory.glob("*.deb")}
    if expected != local:
        raise ValueError("Local Packages index does not match local DEBs")
    tag = "apt-" + suite
    release = gh_json(f"repos/{repo}/releases/tags/{tag}")
    release_id = release["id"]
    # Verify the remote index assets are exactly those just uploaded before deletion.
    with __import__("tempfile").TemporaryDirectory() as temporary:
        tmp = Path(temporary)
        for name in ("Packages", "InRelease"):
            subprocess.run(["gh", "release", "download", tag, "--repo", repo, "--pattern", name, "--dir", str(tmp)], check=True)
            if (tmp / name).read_bytes() != (directory / name).read_bytes():
                raise ValueError("Remote " + name + " differs from newly published local version")
    # --paginate ensures old assets past GitHub's first page are included.
    pages = gh_json("--paginate", "--slurp", f"repos/{repo}/releases/{release_id}/assets?per_page=100")
    assets = [asset for page in pages for asset in page]
    obsolete = obsolete_asset_ids(assets, expected)
    for asset_id, name in obsolete:
        subprocess.run(["gh", "api", "--method", "DELETE", f"repos/{repo}/releases/assets/{asset_id}"], check=True)
        print("Removed obsolete", tag, name, flush=True)
    print(f"{tag}: retained {len(expected)} indexed DEBs, removed {len(obsolete)} outdated DEBs", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--suite", choices=("resolute", "stonking"), required=True)
    args = parser.parse_args()
    prune(args.repo, args.suite, args.directory)


if __name__ == "__main__":
    main()
