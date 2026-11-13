# Soltros Ubuntu

Personal Ubuntu packages, built and distributed entirely through GitHub. Install an app with APT and get future packaged updates through your normal Ubuntu updates. GitHub hosts the packages and repository indexes.

Source recipes, pinned downloads, build checks, update reports, and signed APT publishing live here.

> **Repository status:** Signed APT releases are published through [Releases](https://github.com/soltros/ubuntu_packages/releases). A newly added package appears there only after its complete build passes. Check the [build runs](https://github.com/soltros/ubuntu_packages/actions/workflows/build.yml) for pending packages.

## Packages

**All 22 package definitions are in [packages.json](packages.json).** The [`sources/`](sources/) directory holds only the three locally maintained apps; other packages use pinned upstream code or verified binary downloads. Built `.deb` files are published through [Releases](https://github.com/soltros/ubuntu_packages/releases).

| Install name | Application | Packaging |
|---|---|---|
| `silo` | Silo browser picker with profile support | Verified upstream native binary, desktop entry, icon and Firefox extension host |
| `brave-browser` | Brave browser | Pinned upstream Debian payload, adapted for this APT repository |
| `chatgpt` | ChatGPT desktop | Pinned upstream Debian package |
| `fresh-editor` | Fresh terminal editor | Verified upstream DEB, preserved byte-for-byte |
| `bitwarden` | Bitwarden password manager | Verified upstream desktop DEB |
| `zettlr` | Zettlr Markdown editor | Verified upstream DEB |
| `discord` | Discord desktop client | Verified official DEB |
| `browserclaw` | BrowserOS / BrowserClaw | Verified upstream DEB |
| `codex` | Codex CLI | Official precompiled Linux bundle |
| `hideout` | File encryption app | D source build |
| `lichii` | Lichii emulator | Pinned AppImage extracted in CI into native files; no AppImage runtime |
| `quick-settings-tray` | GNOME Quick Settings system tray | GNOME extension |
| `recomplauncher` | Discover and launch PC recompilations | Official native DEB, adapted to preserve the existing APT package name |
| `sharpemu` | Experimental PS5 emulator | Pinned upstream Linux bundle |
| `termsmith` | GTK terminal configuration editor | Bundled Vala source build |
| `vacuumtube` | YouTube TV desktop client | Verified upstream native DEB |
| `vpn-manager` | Tailscale and WireGuard manager | Bundled Python app |
| `waterfox` | Waterfox browser | Pinned upstream Linux bundle |
| `xemu` | Original Xbox emulator | Native source build using upstream Debian rules |
| `xenia` | Experimental Xbox 360 emulator | Native Linux source build |
| `addwater` | Firefox GNOME theme manager | Python/Meson source build |
| `pantheon-studio` | Pantheon customization app | Bundled Vala source build |

### Native emulator and launcher packages

Lichii is unpacked from its checksum-pinned upstream AppImage during CI and repackaged as ordinary application files and private libraries. It does not compile from source or extract anything at launch. xemu compiles from pinned source inside Ubuntu 26.10. Debian tooling computes runtime library dependencies. RecompLauncher uses upstream's native DEB, adapted to the existing package identity.

No AppImage is shipped or extracted at launch. Both build CI and the signed publisher run `scripts/verify-native.py`: it rejects AppImage filenames, AppImage ELF signatures (including renamed files), and extraction wrappers. xemu and RecompLauncher provide ELF executables under `/usr/bin`; Lichii uses a fixed launcher for its verified private ELF. This also stops an older in-flight wrapper build from being republished after the native transition.

### Vendor Debian applications

Fresh, Bitwarden, Zettlr, Discord and BrowserOS are maintained here rather than downloaded by the post-installer. Their amd64 downloads are versioned and checksum-pinned; CI verifies each DEB's actual package name, version and architecture, then checks dependency resolution in Ubuntu 26.10. Successful builds enter the existing signed APT publication. Install/update them normally:

```bash
sudo apt update
sudo apt install fresh-editor bitwarden zettlr discord browserclaw
sudo apt upgrade
```

Fresh's package version includes a Debian revision (`0.5.8-1`). The BrowserOS asset `0.52.1.1` currently identifies itself as package `browserclaw`, version `155.0.8318.26`. Its `upstream_version` is tracked separately so asset updates are detected despite that mismatch; inspect DEB metadata when changing the pin. No updater infers BrowserOS's version from its differently named Git tag.

The update scan runs daily and when tracking configuration changes, and maintains the existing update issue assigned to `soltros`. Once all upstream pins are current, the issue remains open until the matching package versions are present in the signed APT release; a successful publisher triggers a final scan and closure. It scans stable DEB assets for Fresh, Bitwarden, Zettlr and BrowserOS, excludes unrelated Bitwarden CLI releases and Fresh's Debian-testing build, and uses Discord's official Linux update endpoint. New downloads and upstream SHA256 digests (when supplied) are included in the issue for review. Network failures or missing assets remain explicit errors. No new signing secret or separate publishing setup is needed.

## Supported targets

The package target is **Ubuntu/Kubuntu 26.10 (stonking), amd64**. CI builds and checks dependencies inside an Ubuntu 26.10 container. Kubuntu uses the same Ubuntu package archive. Package compatibility with 26.10 is being validated; earlier Ubuntu releases are not publishing targets.

Pinned arm64 downloads are retained for Brave, ChatGPT, Codex and Waterfox. Lichii has a pinned arm64 AppImage for extraction, and xemu supports source builds on arm64. Termsmith, Pantheon Studio, and VPN Manager also have arm64 recipes. They can be built on an arm64 host, but arm64 is not yet published by the CI.

Pantheon Studio is packaged as a standalone application. Its optional launcher and panel integrations are not included; installing it does not replace your desktop environment.

## Add the APT repository

Run these commands **after a signed release is published**. The commands choose the correct Ubuntu release and use a dedicated keyring. No `trusted=yes` or disabled signature checking is needed.

```bash
sudo apt update
sudo apt install ca-certificates curl gnupg

. /etc/os-release
case "$VERSION_CODENAME" in
  stonking) suite="$VERSION_CODENAME" ;;
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

The flat APT layout is hosted as assets of the `apt-stonking` GitHub Release. Packages use relative filenames in the signed index and can exceed Git's file-size limit. GitHub Pages and an external server are unnecessary.

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
