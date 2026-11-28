#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "${ROOT_DIR}/../aur_pkgbuilds" ]]; then
    AUR_DIR="$(cd "${ROOT_DIR}/../aur_pkgbuilds" && pwd)"
else
    AUR_DIR="${ROOT_DIR}/aur"
fi
MANIFEST="${ROOT_DIR}/packages.json"

DRY_RUN=0
NO_BUILD=0
TARGET_PKG=""

usage() {
    cat <<'EOF'
Usage: update_pkgbuilds.sh [OPTIONS]

Scan upstream release tags/commits for all packaged apps, update any outdated
AUR PKGBUILDs under aur/, print an update report, and pull/build updated
packages with makepkg.

Options:
  --dry-run          Scan and print the report without modifying PKGBUILDs or building
  --no-build         Update PKGBUILDs and print the report, but skip makepkg
  --package <name>   Only check/update a single package (manifest key or AUR pkgname)
  -h, --help         Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --no-build)
            NO_BUILD=1
            shift
            ;;
        --package)
            TARGET_PKG="${2:-}"
            [[ -z "$TARGET_PKG" ]] && { echo "Missing value for --package" >&2; exit 2; }
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

UPDATED_LIST_FILE="$(mktemp)"
trap 'rm -f "$UPDATED_LIST_FILE"' EXIT

python3 - "$ROOT_DIR" "$MANIFEST" "$AUR_DIR" "$DRY_RUN" "$TARGET_PKG" "$UPDATED_LIST_FILE" <<'PY'
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

root_dir = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
aur_dir = Path(sys.argv[3])
dry_run = sys.argv[4] == "1"
target_pkg = sys.argv[5].strip()
updated_list_file = Path(sys.argv[6])

# Reuse the repository's upstream checker and updater helpers
check_spec = importlib.util.spec_from_file_location("check_updates", root_dir / "scripts/check-updates.py")
check_mod = importlib.util.module_from_spec(check_spec)
check_spec.loader.exec_module(check_mod)

auto_spec = importlib.util.spec_from_file_location("auto_update", root_dir / "scripts/auto-update.py")
auto_mod = importlib.util.module_from_spec(auto_spec)
auto_spec.loader.exec_module(auto_mod)

AUR_NAME_MAP = {
    "brave": "brave-bin",
    "chatgpt": "chatgpt-bin",
    "codex": "codex-bin",
    "lichii": "lichii-bin",
    "recomplauncher": "recomplauncher-bin",
    "sharpemu": "sharpemu-bin",
    "waterfox": "waterfox-bin",
    "vacuumtube": "vacuumtube-bin",
    "fresh": "fresh-editor-bin",
    "bitwarden": "bitwarden-bin",
    "zettlr": "zettlr-bin",
    "discord": "discord-bin",
    "browseros": "browseros-bin",
    "silo": "silo-bin",
    "hellonzb": "hellonzb-bin",
    "termsmith": "termsmith",
    "pantheon-studio": "pantheon-studio",
    "vpn-manager": "vpn-manager",
    "quick-settings-tray": "quick-settings-tray",
    "addwater": "addwater",
    "hideout": "hideout",
    "xenia": "xenia",
    "xemu": "xemu",
}


def arch_pkgver(ver: str) -> str:
    """Convert an upstream version into a valid Arch pkgver (no hyphens/colons)."""
    return re.sub(r"[-:\s]+", "_", ver)


def read_pkgbuild_vars(pb_path: Path) -> dict:
    text = pb_path.read_text()
    vars_found = {}
    for key in ("pkgname", "pkgver", "_pkgver", "_commit", "pkgrel"):
        m = re.search(rf"(?m)^{key}=([^\n#]+)", text)
        if m:
            vars_found[key] = m.group(1).strip().strip("'\"")
    return vars_found


def sha256_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "soltros-aur-updater"})
    sha = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=180) as resp:
        while chunk := resp.read(1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def replace_var(text: str, key: str, value: str) -> str:
    return re.sub(rf"(?m)^{key}=.*$", f"{key}={value}", text, count=1)


def update_pkgbuild_file(aur_name: str, pkg_info: dict, row: dict) -> None:
    pb_path = aur_dir / aur_name / "PKGBUILD"
    text = pb_path.read_text()
    latest = row["latest"]
    track = pkg_info.get("track", {})
    tkind = track.get("kind")

    if tkind == "commit":
        new_commit = latest
        text = replace_var(text, "_commit", new_commit)
        if aur_name == "xenia":
            text = replace_var(text, "pkgver", f"0.r0.g{new_commit[:7]}")
        text = replace_var(text, "pkgrel", "1")
        pb_path.write_text(text)
        return

    # Tag / release / release_asset / chatgpt / discord
    updated_manifest = auto_mod.update_one(
        aur_name.removesuffix("-bin") if aur_name != "fresh-editor-bin" else "fresh",
        pkg_info,
        row,
    ) if pkg_info.get("kind") in ("deb", "archive", "appdir") else None

    if updated_manifest is not None:
        raw_ver = updated_manifest["version"]
        arch_ver = arch_pkgver(raw_ver)
        if re.search(r"(?m)^_pkgver=", text):
            text = replace_var(text, "_pkgver", raw_ver)
        text = replace_var(text, "pkgver", arch_ver)
        text = replace_var(text, "pkgrel", "1")

        downloads = updated_manifest.get("downloads", {})
        if "amd64" in downloads and "arm64" in downloads:
            text = re.sub(
                r"(?m)^sha256sums_x86_64=\([^)]*\)",
                f"sha256sums_x86_64=('{downloads['amd64']['sha256']}')",
                text,
            )
            text = re.sub(
                r"(?m)^sha256sums_aarch64=\([^)]*\)",
                f"sha256sums_aarch64=('{downloads['arm64']['sha256']}')",
                text,
            )
        elif "amd64" in downloads:
            # For release_asset packages like browseros where the URL tag also changes
            if tkind == "release_asset":
                url = downloads["amd64"]["url"]
                # Keep PKGBUILD parameterized if possible, otherwise set exact URL
                if re.search(r"(?m)^source=\(", text):
                    text = re.sub(
                        r"(?m)^source=\([^)]*\)",
                        f'source=("{url}")',
                        text,
                    )
                    noext_name = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
                    if re.search(r"(?m)^noextract=\(", text):
                        text = re.sub(
                            r"(?m)^noextract=\([^)]*\)",
                            f'noextract=("{noext_name}")',
                            text,
                        )
            text = re.sub(
                r"(?m)^sha256sums=\([^)]*\)",
                f"sha256sums=('{downloads['amd64']['sha256']}')",
                text,
            )
    else:
        # Source-built release/tag packages (addwater, hideout, xemu, xemu-perf)
        arch_ver = arch_pkgver(latest)
        text = replace_var(text, "pkgver", arch_ver)
        text = replace_var(text, "pkgrel", "1")
        if re.search(r"(?m)^_commit=", text) and track.get("repo"):
            tag = track.get("prefix", "") + latest
            commit_info = auto_mod.get_json(
                f"https://api.github.com/repos/{track['repo']}/commits/{urllib.parse.quote(tag, safe='')}"
            )
            text = replace_var(text, "_commit", commit_info["sha"])

    pb_path.write_text(text)


packages = json.loads(manifest_path.read_text())

# Include xemu-perf which shares xemu's upstream tracking
entries = list(packages.items())
if "xemu" in packages:
    entries.append(("xemu-perf", packages["xemu"]))

rows = []
updated_aur_pkgs = []

for key, p in entries:
    aur_name = "xemu-perf" if key == "xemu-perf" else AUR_NAME_MAP.get(key, key)
    if target_pkg and target_pkg not in (key, aur_name):
        continue
    pb_path = aur_dir / aur_name / "PKGBUILD"
    if not pb_path.is_file():
        rows.append({"aur": aur_name, "status": "error", "current": "missing", "latest": "unknown", "error": f"Missing {pb_path}"})
        continue

    pb_vars = read_pkgbuild_vars(pb_path)
    if p.get("track", {}).get("kind") == "commit":
        pb_current = pb_vars.get("_commit") or pb_vars.get("pkgver", "unknown")
    else:
        pb_current = pb_vars.get("_pkgver") or pb_vars.get("pkgver", "unknown")

    try:
        row = check_mod.check(p)
        latest = row["latest"]
        if row["status"] == "local":
            rows.append({"aur": aur_name, "status": "local", "current": pb_current, "latest": "bundled source"})
            continue

        # Compare against the PKGBUILD's own current version/commit
        is_update = False
        if p.get("track", {}).get("kind") == "commit":
            is_update = not latest.startswith(pb_current)
        else:
            is_update = (latest != pb_current) and (arch_pkgver(latest) != pb_vars.get("pkgver"))

        if is_update:
            row["status"] = "update"
            if not dry_run:
                try:
                    update_pkgbuild_file(aur_name, p, row)
                    updated_aur_pkgs.append(aur_name)
                except Exception as exc:
                    rows.append({"aur": aur_name, "status": "error", "current": pb_current, "latest": latest, "error": f"PKGBUILD update failed: {exc}"})
                    continue
            else:
                updated_aur_pkgs.append(aur_name)
            rows.append({"aur": aur_name, "status": "update", "current": pb_current, "latest": latest})
        else:
            rows.append({"aur": aur_name, "status": "current", "current": pb_current, "latest": latest})
    except Exception as exc:
        rows.append({"aur": aur_name, "status": "error", "current": pb_current, "latest": "unknown", "error": str(exc)})

# Print report
updates = [r for r in rows if r["status"] == "update"]
errors = [r for r in rows if r["status"] == "error"]

print("# AUR PKGBUILD Update Report\n")
print(f"Scanned: {len(rows)} | Updates: {len(updates)} | Errors: {len(errors)}\n")
print(f"{'Package':<24} {'Status':<10} {'Current':<24} {'Latest'}")
print(f"{'-'*24} {'-'*10} {'-'*24} {'-'*24}")
for r in rows:
    print(f"{r['aur']:<24} {r['status']:<10} {r['current']:<24} {r['latest']}")

if updates:
    print("\n## Updates Available:")
    for r in updates:
        action = "(dry-run)" if dry_run else "(PKGBUILD updated)"
        print(f"  - {r['aur']}: {r['current']} -> {r['latest']} {action}")

if errors:
    print("\n## Errors:")
    for r in errors:
        print(f"  - {r['aur']}: {r.get('error')}")

updated_list_file.write_text("\n".join(updated_aur_pkgs) + ("\n" if updated_aur_pkgs else ""))
PY

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo ""
    echo "[dry-run] Skipping build step."
    exit 0
fi

if [[ "$NO_BUILD" -eq 1 ]]; then
    echo ""
    echo "[--no-build] Skipping build step."
    exit 0
fi

if [[ ! -s "$UPDATED_LIST_FILE" ]]; then
    echo ""
    echo "All AUR PKGBUILDs are up to date. Nothing to build."
    exit 0
fi

echo ""
if ! command -v makepkg >/dev/null 2>&1; then
    echo "Warning: 'makepkg' is not installed on this system (not Arch Linux)." >&2
    echo "Updated PKGBUILDs were written, and syntax was checked, but package building requires makepkg." >&2
    while IFS= read -r pkg; do
        [[ -z "$pkg" ]] && continue
        bash -n "${AUR_DIR}/${pkg}/PKGBUILD"
        echo "  [syntax ok] ${AUR_DIR}/${pkg}/PKGBUILD"
    done < "$UPDATED_LIST_FILE"
    exit 0
fi

echo "## Pulling sources and building updated packages..."
while IFS= read -r pkg; do
    [[ -z "$pkg" ]] && continue
    echo "==> Building ${pkg}..."
    (
        cd "${AUR_DIR}/${pkg}"
        makepkg -s --noconfirm --needed
    )
done < "$UPDATED_LIST_FILE"
