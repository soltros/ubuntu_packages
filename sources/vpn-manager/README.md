# VPN Manager

A small GTK4/libadwaita desktop app for switching between Tailscale and
NetworkManager WireGuard profiles. Includes live status, config import, disconnect,
and profile removal. Each switch verifies that the old connection stopped before
starting the next. A failed connection can leave you disconnected; no automatic
rollback or kill switch is provided.

## Run locally

```sh
nix run path:/home/derrik/soltros_nixpkgs#vpn-manager
```

Or add `vpn-manager` from this repository's overlay to `environment.systemPackages`.
The package does not change your system configuration. On NixOS enable:

```nix
networking.networkmanager.enable = true;
services.tailscale.enable = true;
security.polkit.enable = true;
users.users.derrik.extraGroups = [ "networkmanager" ];
```

Use your actual username. A desktop polkit authentication agent is required.
VPN Manager starts a privileged helper through pkexec at launch. Approve the
administrator prompt once per app session; cancelling keeps controls locked until
Refresh retries authentication. The GUI runs as your normal user. The helper exits
when the app closes, accepts only VPN operations over private pipes, and serializes
switches across running instances. Tailscale login remains in its own setup workflow.

## Behavior

- Tailscale and WireGuard can coexist with carefully configured routes. This app
  deliberately enforces one connection at a time for switches made through it.
- Exclusivity is enforced for connections started in VPN Manager, including a
  shutdown wait and a check after activation. It is not a background enforcement daemon: other apps and system services can
  still activate connections. Overlapping connections are flagged when detected.
- WireGuard status means the interface/profile is active, not proof of a recent
  handshake or working internet access. Tailscale being on does not imply use of
  an exit node.
- Imports are initially temporary, then saved with autoconnect disabled. Managed
  profiles also have autoconnect disabled when connected/disconnected here.
- Configs containing wg-quick hooks or SaveConfig are rejected because those
  semantics cannot be safely preserved by NetworkManager. Scripts are never run.
- NetworkManager stores the imported keys. The app does not log configs or display
  raw command failures that might contain secrets. Keep your original config safe.
- Kernel WireGuard interfaces managed by wg-quick, networkd, or another tool are
  detected and block switching. Stop them with their original manager first.
- Both NetworkManager and tailscaled must be available to verify safe switching.
- Existing settings are preserved when reconnecting Tailscale with `tailscale up`.

## Tests

```sh
cd pkgs/vpn-manager
python3 -m unittest discover -s tests -v
```

Tests use simulated network state; they never change live connections.

## Debian / Ubuntu package

Targets Debian 12+ and Ubuntu 24.04+ with GTK 4.8+ and libadwaita 1.2+.
The architecture-independent package works on systems with those dependencies.
Install Tailscale from its [official instructions](https://tailscale.com/docs/install/linux)
first, then install the downloaded package:

```sh
sudo apt install ./vpn-manager_0.2.0_all.deb
```

NetworkManager and tailscaled need to be running. Use a desktop session with a
polkit authentication agent. No installer scripts change services, networking,
Tailscale login, or user permissions automatically.

Build the archive on NixOS:

```sh
nix build path:/home/derrik/soltros_nixpkgs#vpn-manager-deb
```

Or from this directory on Debian/Ubuntu with `python3` and `dpkg` installed:

```sh
python3 build-deb.py --output dist
```
