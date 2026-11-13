# Soltros Ubuntu

Personal Ubuntu packages, built and distributed entirely through GitHub. Install an app with APT and get future packaged updates through your normal Ubuntu updates. GitHub hosts the packages and repository indexes.

Source recipes, pinned downloads, build checks, update reports, and signed APT publishing live here.

> **Repository status:** Signed APT releases are published through [Releases](https://github.com/soltros/ubuntu_packages/releases). A newly added package appears there only after its complete build passes. Check the [build runs](https://github.com/soltros/ubuntu_packages/actions/workflows/build.yml) for pending packages.

## Packages

<!-- BEGIN GENERATED PACKAGE LIST -->

**22 standard definitions in [packages.json](packages.json), plus the independently built `xemu-perf` definition.**

Targets: Ubuntu/Kubuntu 26.04 (`resolute`), Ubuntu/Kubuntu 26.10 (`stonking`). Each release must pass its own CI checks before publication.

| Install name | Description | Pinned version | Architectures | Packaging | Update tracking | Definition |
|---|---|---|---|---|---|---|
| `addwater` | Addwater | 1.3 | amd64 | Meson source build | Upstream tag; daily assigned issue | [packages.json](packages.json) |
| `bitwarden` | Bitwarden password manager | 2026.10.4 | amd64 | Upstream native DEB | Upstream release_asset; daily assigned issue | [packages.json](packages.json) |
| `brave-browser` | Brave | 1.99.57 | amd64, arm64 | Upstream native DEB; adapted for existing package identity/repository | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `browserclaw` | BrowserOS (BrowserClaw) browser | 155.0.8318.26 | amd64 | Upstream native DEB | Upstream release_asset; daily assigned issue | [packages.json](packages.json) |
| `chatgpt` | Chatgpt | 26.1111.21308 | amd64, arm64 | Upstream native DEB | Upstream chatgpt; daily assigned issue | [packages.json](packages.json) |
| `codex` | Codex | 0.169.0 | amd64, arm64 | Upstream native binary archive | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `discord` | Discord desktop client | 1.0.169 | amd64 | Upstream native DEB | Upstream discord; daily assigned issue | [packages.json](packages.json) |
| `fresh-editor` | Fresh terminal editor | 0.5.8-1 | amd64 | Upstream native DEB | Upstream release_asset; daily assigned issue | [packages.json](packages.json) |
| `hideout` | Hideout | 0.9.13 | amd64 | D source build | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `lichii` | Lichii native Switch emulator | 177 | amd64, arm64 | AppImage unpacked in CI; native files in DEB | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `pantheon-studio` | Pantheon Studio | 0.2.0 | amd64, arm64 | Meson source build | Locally maintained source | [packages.json](packages.json) |
| `quick-settings-tray` | Quick Settings Tray | 1 | amd64 | GNOME Shell extension | Upstream commit; daily assigned issue | [packages.json](packages.json) |
| `recomplauncher` | RecompLauncher native desktop application | 0.90.0-beta.42 | amd64 | Upstream native DEB; adapted for existing package identity/repository | Upstream prerelease; daily assigned issue | [packages.json](packages.json) |
| `sharpemu` | Sharpemu | 0.0.7-pulse | amd64 | Upstream native binary archive | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `silo` | Silo browser picker with browser profile support | 1.2.2 | amd64 | Upstream native binary archive | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `termsmith` | Termsmith | 0.2.0 | amd64, arm64 | Meson source build | Locally maintained source | [packages.json](packages.json) |
| `vacuumtube` | VacuumTube YouTube TV desktop client | 2.0.1 | amd64, arm64 | Upstream native DEB | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `vpn-manager` | Vpn Manager | 0.2.0 | amd64, arm64 | Bundled Python app | Locally maintained source | [packages.json](packages.json) |
| `waterfox` | Waterfox | 6.7.8 | amd64, arm64 | Upstream native binary archive | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `xemu` | Native original Xbox emulator | 0.8.139 | amd64, arm64 | Native source build with upstream Debian rules | Upstream release; daily assigned issue | [packages.json](packages.json) |
| `xenia` | Xenia | 0~git95a5c3e | amd64 | Native Linux source build | Upstream commit; daily assigned issue | [packages.json](packages.json) |
| `zettlr` | Zettlr Markdown editor | 4.10.0 | amd64 | Upstream native DEB | Upstream release_asset; daily assigned issue | [packages.json](packages.json) |
| `xemu-perf` | XEMU (Optimizations) | 0.8.139-1soltrosperf1 (+ target suite) | amd64 | Native source build with pinned Vulkan cache patch | Dedicated daily source/patch checks and assigned issue | [package.json](experiments/xemu/package.json) |

Versions above are definition pins, not a claim that every build has been published. Check the matching [signed release](https://github.com/soltros/ubuntu_packages/releases) for availability.

The [`sources/`](sources/) directory holds locally maintained applications. Download hashes, build dependencies, and upstream tracking are recorded in the linked definitions.

<!-- END GENERATED PACKAGE LIST -->

### Native emulator and launcher packages

Lichii is unpacked from its checksum-pinned upstream AppImage during CI and repackaged as ordinary application files and private libraries. It does not compile from source or extract anything at launch. xemu compiles from pinned source inside each target Ubuntu release. Debian tooling computes runtime library dependencies. RecompLauncher uses upstream's native DEB, adapted to the existing package identity.

No AppImage is shipped or extracted at launch. Both build CI and the signed publisher run `scripts/verify-native.py`: it rejects AppImage filenames, AppImage ELF signatures (including renamed files), and extraction wrappers. xemu and RecompLauncher provide ELF executables under `/usr/bin`; Lichii uses a fixed launcher for its verified private ELF. This also stops an older in-flight wrapper build from being republished after the native transition.

### Vendor Debian applications

Fresh, Bitwarden, Zettlr, Discord and BrowserOS are maintained here rather than downloaded by the post-installer. Their amd64 downloads are versioned and checksum-pinned; CI verifies each DEB's actual package name, version and architecture, then checks dependency resolution independently in Ubuntu 26.04 and 26.10. Successful builds enter the existing signed APT publication. Install/update them normally:

```bash
sudo apt update
sudo apt install fresh-editor bitwarden zettlr discord browserclaw
sudo apt upgrade
```

Fresh's package version includes a Debian revision (`0.5.8-1`). The BrowserOS asset `0.52.1.1` currently identifies itself as package `browserclaw`, version `155.0.8318.26`. Its `upstream_version` is tracked separately so asset updates are detected despite that mismatch; inspect DEB metadata when changing the pin. No updater infers BrowserOS's version from its differently named Git tag.

The update scan runs daily and when tracking configuration changes, and maintains the existing update issue assigned to `soltros`. Once all upstream pins are current, the issue remains open until the matching package versions are present in the signed APT release; a successful publisher triggers a final scan and closure. It scans stable DEB assets for Fresh, Bitwarden, Zettlr and BrowserOS, excludes unrelated Bitwarden CLI releases and Fresh's Debian-testing build, and uses Discord's official Linux update endpoint. New downloads and upstream SHA256 digests (when supplied) are included in the issue for review. Network failures or missing assets remain explicit errors. No new signing secret or separate publishing setup is needed.

## Supported targets

The package targets are **Ubuntu/Kubuntu 26.04 (resolute) and 26.10 (stonking), amd64**. CI builds and validates each target in its own container. Kubuntu uses the same Ubuntu package archive.

Pinned arm64 downloads are retained for Brave, ChatGPT, Codex and Waterfox. Lichii has a pinned arm64 AppImage for extraction, and xemu supports source builds on arm64. Termsmith, Pantheon Studio, and VPN Manager also have arm64 recipes. They can be built on an arm64 host, but arm64 is not yet published by the CI.

Pantheon Studio is packaged as a standalone application. Its optional launcher and panel integrations are not included; installing it does not replace your desktop environment.

## Add the APT repository

Run these commands **after a signed release is published**. The commands choose the correct Ubuntu release and use a dedicated keyring. No `trusted=yes` or disabled signature checking is needed.

```bash
sudo apt update
sudo apt install ca-certificates curl gnupg

. /etc/os-release
case "$VERSION_CODENAME" in
  resolute|stonking) suite="$VERSION_CODENAME" ;;
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

The flat APT layout is hosted as assets of the matching `apt-resolute` or `apt-stonking` GitHub Release. Packages use relative filenames in the signed index and can exceed Git's file-size limit. GitHub Pages and an external server are unnecessary.

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
- **Check upstream updates:** checks upstream releases, stable tags and branches daily, with stable-only tracking for stable apps and prereleases for RecompLauncher. It maintains one update issue assigned to `soltros` and saves JSON/Markdown reports. Network/API failures are shown as errors, never as “up to date.” Bundled apps are reported separately as local source.
- **Publish signed APT repository:** publishes only after the entire trusted main-branch build succeeds. PR artifacts cannot trigger a trusted publication. A weekly refresh renews signed metadata for the last working package set. Metadata expires after 14 days, so a stalled publisher is visible to APT.

Upstream scanning reports updates for review; it does not blindly replace versions or checksums. To update a binary package, change its version, versioned URL, and SHA256 in `packages.json`. Update all supported architecture pins together. For source packages, update the pinned `rev` and Debian version. Commit to `main`; successful checks trigger publishing.

Publishing uses a single concurrency group. GitHub Release uploads are not an atomic transaction: clients can briefly see an index mismatch during an update and should retry `apt update`. A failed build leaves the previously published packages available.

## Build and test locally

Use a clean host/container matching the target Ubuntu release. Install the common tools and the package-specific `build_depends` listed in `packages.json`:

```bash
sudo apt install python3 git ca-certificates dpkg-dev debhelper fakeroot build-essential
python3 scripts/build.py vpn-manager --suite stonking
python3 -m unittest discover -s tests -v
```

For example, Termsmith also needs Meson, Ninja, pkg-config, Vala, GTK4, Granite 7, and Gee development packages. D, Electron, and Xenia build dependencies are fetched in their isolated build jobs. Do not run builds from an untrusted checkout as root on your workstation.

`dist/` contains the generated `.deb` files. `scripts/repository.py` generates `Packages`, `Packages.gz`, `Release`, `InRelease`, `Release.gpg`, the public key, and checksums from a set of built packages.

## Remove the repository

```bash
sudo rm /etc/apt/sources.list.d/soltros.list /etc/apt/keyrings/soltros.asc
sudo apt update
```

Already installed packages remain installed. Remove individual applications with `sudo apt remove package-name`.

## Licensing

Repository packaging additions use GPL-3.0 as provided in [LICENSE](LICENSE). Applications retain their respective upstream licenses and trademarks; packaging does not relicense them. ChatGPT’s upstream Debian package is preserved byte-for-byte. Brave’s payload is repackaged to remove its upstream repository/keyring bootstrap and use this repository’s signing setup. Bundled VPN Manager retains its own MIT license. See each application's source and license notices.

## Independent optimized xemu

`XEMU (Optimizations)` is provided by optional package `xemu-perf`, installed alongside stable `xemu`. Its dedicated workflow builds only that package and merges it into the signed APT repository. See [the experiment notes](experiments/xemu/README.md) for the Vulkan cache patch, isolated settings, audio comparison options, and limits.

Manifest-only package changes (including supporting code in the same commit) select changed recipes rather than rebuilding the entire matrix. Shared build changes without recipe changes rebuild the matrix. Publication overlays the successful package set and retains unrelated packages.

### Silo browser picker

Install with `sudo apt install silo`, then launch **Silo**. Choose whether to register it as your default browser from inside the application; package installation does not change your current browser. The native amd64 release is checksum-pinned, checked on Ubuntu 26.10, and tracked by the normal daily update issue assigned to `soltros`. Only Silo builds when its recipe changes.

The package includes its HTTP/HTTPS desktop entry, icon, MIT licence, and Firefox native-messaging host. Use `sudo apt remove silo` to uninstall the packaged application; upstream's built-in uninstall is intended for a user-local installation. Existing browser defaults and user configuration are not modified by DEB maintainer scripts.

## Ubuntu 26.04 and 26.10

Both Ubuntu/Kubuntu releases have independent container builds and dependency checks:

| Release | Codename | Signed release |
|---|---|---|
| 26.04 LTS | resolute | `apt-resolute` |
| 26.10 | stonking | `apt-stonking` |

The optimized xemu workflow also builds both versions. Source-built DEBs carry the target suite in their version. Vendor DEBs are independently checked against each Ubuntu release. Artifact recovery only accepts jobs for the matching suite; publishing never copies another Ubuntu release's build into your index. The update checker tracks one set of upstream pins and checks that both signed releases contain those versions.

Use the matching suite in the APT setup commands below (run only after the matching signed release has been published):

```bash
. /etc/os-release
case "$VERSION_CODENAME" in resolute|stonking) suite="$VERSION_CODENAME" ;; *) echo 'Unsupported Ubuntu release'; exit 1 ;; esac
base="https://github.com/soltros/ubuntu_packages/releases/download/apt-$suite"
curl -fsSL "$base/soltros-archive-keyring.asc" | gpg --dearmor | sudo tee /etc/apt/keyrings/soltros.gpg >/dev/null
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/soltros.gpg] $base ./" | sudo tee /etc/apt/sources.list.d/soltros.list
sudo apt update
```

This extends the package repository; the separate desktop post-installer still targets Kubuntu 26.10.

## Keeping the package catalogue current

The package list above is generated from `packages.json`, the optimized xemu definition, and `scripts/suites.json`. After adding/removing a package or changing its pin, architecture, packaging kind or update tracking, run:

```bash
python3 docs/package-list.py
python3 docs/package-list.py --check
```

The dedicated documentation workflow checks pull requests and automatically synchronizes the README on main. It does not start package builds for documentation-only updates.
