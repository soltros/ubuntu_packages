# Soltros Ubuntu

Personal Ubuntu packages, built and distributed entirely through GitHub. Install an app with APT and get future packaged updates through your normal Ubuntu updates. No Nix or Launchpad account is required to use the packages.

This is the Ubuntu successor to [soltros_nixpkgs](https://github.com/soltros/soltros_nixpkgs). Source recipes, pinned downloads, bundled applications, build checks, update reports, and signed APT publishing live here.

> **Bootstrap status:** Packaging is being migrated. The repository becomes installable after the package build checks pass and the maintainer configures the signing secret once. An app having a recipe here does not mean its Ubuntu build has passed yet. Check the [build runs](https://github.com/soltros/ubuntu_packages/actions/workflows/build.yml) and [Releases](https://github.com/soltros/ubuntu_packages/releases) before installing. Publishing deliberately waits for the complete package set to pass.

## Packages

| Install name | Application | Packaging |
|---|---|---|
| `brave-browser` | Brave browser | Pinned upstream Debian package |
| `cabinet-desktop` | Cabinet file locker client | Rust source build |
| `chatgpt` | ChatGPT desktop | Pinned upstream Debian package |
| `codex` | Codex CLI | Official precompiled Linux bundle |
| `hideout` | File encryption app | D source build |
| `lichii` | Lichii emulator | Pinned AppImage with a launcher that does not require FUSE |
| `quick-settings-tray` | GNOME Quick Settings system tray | GNOME extension |
| `recomplauncher` | Discover and launch PC recompilations | Pinned AppImage with a launcher that does not require FUSE |
| `sharpemu` | Experimental PS5 emulator | Pinned upstream Linux bundle |
| `supernova-desktop` | Supernova music client | Flutter source build |
| `termsmith` | GTK terminal configuration editor | Bundled Vala source build |
| `vacuumtube` | YouTube TV desktop client | Electron source build |
| `vpn-manager` | Tailscale and WireGuard manager | Bundled Python app |
| `waterfox` | Waterfox browser | Pinned upstream Linux bundle |
| `xenia` | Experimental Xbox 360 emulator | Native Linux source build |
| `addwater` | Firefox GNOME theme manager | Python/Meson source build |
| `pantheon-studio` | Pantheon customization app | Bundled Vala source build |

The old `vpn-manager-deb` output is the same application as `vpn-manager`; install `vpn-manager`. The Nix `brave` attribute becomes Ubuntu's upstream `brave-browser` name.

Grayjay, Keyguard, Flakebuilder, Flakebuilder GUI, Nixboutique, and nixpkger are excluded by request. There is no dependency on the old Nix repository. `migration.json` accounts for every former exported package and these exclusions.

## Supported targets

The CI builds separate **Ubuntu 24.04 LTS (noble)** and **Ubuntu 26.04 LTS (resolute)** packages on amd64. Packages and their dependencies are checked inside the corresponding Ubuntu image. Do not use one series' repository on another Ubuntu release. Other releases are not currently validated.

Pinned arm64 downloads are retained for Brave, ChatGPT, Codex, Lichii, and Waterfox. Termsmith, Pantheon Studio, and VPN Manager also have arm64 recipes. They can be built on an arm64 host, but arm64 is not yet published by the CI.

Pantheon Studio's application source is included. Its old NixOS module and version-specific Wingpanel panel/menu patches are retained in `sources/pantheon-studio` as reference; the Ubuntu package does **not** replace Ubuntu's desktop shell or apply those integrations. Installing the app alone does not provide the complete patched Pantheon session.

## Add the APT repository

Run these commands **after a signed release is published**. The commands choose the correct Ubuntu release and use a dedicated keyring. No `trusted=yes` or disabled signature checking is needed.

```bash
sudo apt update
sudo apt install ca-certificates curl gnupg

. /etc/os-release
case "$VERSION_CODENAME" in
  noble|resolute) suite="$VERSION_CODENAME" ;;
  *) echo "This Ubuntu release is not supported yet"; exit 1 ;;
esac

base="https://github.com/soltros/ubuntu_packages/releases/download/apt-$suite"
curl -fL "$base/soltros-archive-keyring.asc" -o /tmp/soltros-archive-keyring.asc
gpg --show-keys --with-fingerprint /tmp/soltros-archive-keyring.asc
# Compare the fingerprint with the maintainer's independently shared fingerprint.
sudo install -Dm644 /tmp/soltros-archive-keyring.asc /etc/apt/keyrings/soltros.asc

printf 'deb [arch=amd64 signed-by=/etc/apt/keyrings/soltros.asc] %s ./\n' "$base" |
  sudo tee /etc/apt/sources.list.d/soltros.list
sudo apt update
sudo apt install codex waterfox vpn-manager
```

The flat APT layout is hosted as assets of the `apt-noble` and `apt-resolute` GitHub Releases. Packages use relative filenames in the signed index and can exceed Git's file-size limit. GitHub Pages and an external server are unnecessary.

For a single application, download its `.deb` from the matching release and run:

```bash
sudo apt install ./package_version_amd64.deb
```

APT resolves dependencies for you. Plain `dpkg -i` does not.

### VPN Manager

WireGuard management uses NetworkManager and polkit. Tailscale is optional and is recommended rather than a mandatory dependency because it is not in Ubuntu's default repositories. Install Tailscale from its official repository if you want that integration. The app never bundles a Tailscale daemon.

### GNOME extension

After installing `quick-settings-tray`, log out and back in, then enable it:

```bash
gnome-extensions enable quick-settings-tray@soltros
```

GNOME Shell compatibility is constrained by the extension's upstream `metadata.json`. A successful package build does not imply compatibility with every GNOME Shell version.

## Maintainer setup (once)

Install GitHub CLI and GnuPG, authenticate `gh` to an account with repository administration access, then run:

```bash
git clone https://github.com/soltros/ubuntu_packages.git
cd ubuntu_packages
bash scripts/setup-signing.sh
```

The script generates a dedicated RSA4096 signing key, saves its private half as the **`APT_SIGNING_KEY` Actions secret**, saves the fingerprint as the **`APT_SIGNING_KEY_ID` repository variable**, writes a local private backup, and starts a package build. It never commits the private key. Keep the backup somewhere secure and share the public fingerprint with clients. Do not rerun the script to fix a build failure: that would replace your repository's trust key. Rotate keys deliberately.

The existing GitHub connection used to prepare this repository cannot create repository secrets. Until this step is complete, the publisher fails with an explicit setup message instead of publishing unsigned packages.

## How automation works

- **Build Ubuntu packages:** runs on package-related pushes, pull requests, or manual dispatch. Each app gets an isolated Ubuntu build for each supported release. Downloads are SHA256 checked. Source builds use pinned upstream revisions. Debian metadata, archive contents, and dependency resolution are checked. Build artifacts are kept for 14 days.
- **Check upstream updates:** checks upstream releases and branches daily, with stable-only tracking for stable apps and prereleases for RecompLauncher. It maintains one update issue and saves JSON/Markdown reports. Network/API failures are shown as errors, never as “up to date.” Bundled apps are reported separately as local source.
- **Publish signed APT repository:** publishes only after the entire trusted main-branch build succeeds. PR artifacts cannot trigger a trusted publication. A weekly refresh renews signed metadata for the last working package set. Metadata expires after 14 days, so a stalled publisher is visible to APT.

Upstream scanning reports updates for review; it does not blindly replace versions or checksums. To update a binary package, change its version, versioned URL, and SHA256 in `packages.json`. Update all supported architecture pins together. For source packages, update the pinned `rev` and Debian version. Commit to `main`; successful checks trigger publishing. No Nix hash calculation is involved.

Publishing uses a single concurrency group. GitHub Release uploads are not an atomic transaction: clients can briefly see an index mismatch during an update and should retry `apt update`. A failed build leaves the previously published packages available.

## Build and test locally

Use a clean host/container matching the target Ubuntu release. Install the common tools and the package-specific `build_depends` listed in `packages.json`:

```bash
sudo apt install python3 git ca-certificates dpkg-dev debhelper fakeroot build-essential
python3 scripts/build.py vpn-manager --suite noble
python3 -m unittest discover -s tests -v
```

For example, Termsmith also needs Meson, Ninja, pkg-config, Vala, GTK4, Granite 7, and Gee development packages. Supernova requires Flutter 3.35.7 in `PATH`; CI installs it. Rust, D, Electron, Flutter, and Xenia build dependencies are fetched in their isolated build jobs. Do not run builds from an untrusted checkout as root on your workstation.

`dist/` contains the generated `.deb` files. `scripts/repository.py` generates `Packages`, `Packages.gz`, `Release`, `InRelease`, `Release.gpg`, the public key, and checksums from a set of built packages.

## Remove the repository

```bash
sudo rm /etc/apt/sources.list.d/soltros.list /etc/apt/keyrings/soltros.asc
sudo apt update
```

Already installed packages remain installed. Remove individual applications with `sudo apt remove package-name`.

## Licensing

Repository packaging additions use GPL-3.0 as provided in [LICENSE](LICENSE). Applications retain their respective upstream licenses and trademarks; packaging does not relicense them. Upstream Debian packages are preserved byte-for-byte. Bundled VPN Manager retains its own MIT license. See each application's source and license notices.
