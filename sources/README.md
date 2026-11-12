# Bundled application source

This directory contains the source code maintained directly in this repository:

- [Termsmith](termsmith/)
- [Pantheon Studio](pantheon-studio/)
- [VPN Manager](vpn-manager/)

**The complete set of 16 Ubuntu package definitions is in [packages.json](../packages.json).** The remaining applications are fetched from pinned upstream repositories or checksum-verified downloads during the build. Their code does not need to be copied into this directory to produce a Debian package.

The [package table](../README.md#packages) lists every application and its packaging method. [scripts/build.py](../scripts/build.py) builds the packages. Installable `.deb` files belong in [GitHub Releases](https://github.com/soltros/ubuntu_packages/releases), rather than this source directory.

Package definitions are not proof of a completed release: check the build results and published release assets for availability.
