# Termsmith

Termsmith is a small Pantheon-native launcher for reusable Alacritty terminal
profiles. It is built with GTK 4, Granite 7, and Vala.

Profiles contain a display name, icon, working folder, and optional startup command.
Termsmith stores them in `$XDG_CONFIG_HOME/termsmith/profiles.ini`. The **Create
Shortcut** button writes a corresponding desktop entry to
`$XDG_DATA_HOME/applications`, so it appears in Pantheon's Applications menu.

Click the icon field to search every icon exposed by the active desktop icon
theme. The chosen icon appears in Termsmith's profile list and in the generated
Applications-menu shortcut. Existing profiles default to `utilities-terminal`.

## Build from the system flake

```sh
nix build .#termsmith
nix run .#termsmith
```

The package is also included in `environment.systemPackages`; applying the
NixOS configuration installs Termsmith and Alacritty system-wide.
