# Termsmith

A GTK4 and Granite application for managing reusable Alacritty terminal profiles.
Profiles contain a display name, icon, working directory, and optional startup command.
They are stored in `$XDG_CONFIG_HOME/termsmith/profiles.ini`.

Install from the Soltros Ubuntu APT repository:

```bash
sudo apt install termsmith alacritty
```

Run `termsmith` or open it from your application menu. Create Shortcut writes
an application entry to `$XDG_DATA_HOME/applications`.

To build a Debian package from this repository's root:

```bash
python3 scripts/build.py termsmith --suite stonking
```

Build dependencies are listed in `packages.json`. Use an Ubuntu release matching
the target suite.
