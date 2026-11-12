# VPN Manager

A GTK4/libadwaita desktop app for switching between Tailscale and NetworkManager
WireGuard profiles. It provides connection status, configuration import,
disconnect, and profile removal.

```bash
sudo apt install vpn-manager
```

For a downloaded package instead:

```bash
sudo apt install ./vpn-manager_*_amd64.deb
```

Use an Ubuntu desktop session with a polkit authentication agent. NetworkManager
must be running. Install Tailscale using its official Ubuntu instructions and sign
in before using its integration. The package does not configure accounts, routes,
or services on your behalf.

The app authenticates through `pkexec` once per session. The GUI runs as your
normal user; a narrowly scoped helper handles privileged operations. It exits
when the app closes. Cancelling authentication leaves controls locked until you
retry. Switching verifies that the previous connection has stopped first.

WireGuard status shows an active interface, not proof of a recent handshake.
Configurations containing shell hooks or SaveConfig are rejected. Other network
managers can still activate connections independently; this app is not a kill switch.

Build and test from the repository root:

```bash
python3 scripts/build.py vpn-manager --suite stonking
PYTHONPATH=sources/vpn-manager python3 -m unittest discover -s sources/vpn-manager/tests -v
```

Tests simulate connection state and do not change live networking.
