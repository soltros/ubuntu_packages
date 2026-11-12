# Pantheon Studio

A Vala, GTK4, and Granite application for editing application names, icons, and
menu visibility. Overrides are stored in your user application directory.

```bash
sudo apt install pantheon-studio
```

Restore Defaults restores the original local application entry or removes the
override to reveal the system entry. Recovery records live in
`$XDG_STATE_HOME/pantheon-studio/backups`. Restore changes before uninstalling
if you want to remove your overrides. Symlinks are rejected to avoid modifying
managed files. External edits are detected before saving.

Desktop settings apply when the relevant settings schemas are available.
Launcher folder, layout, and panel appearance controls need compatible Pantheon
desktop integrations; these are not included in this standalone Ubuntu package.
Installing the application does not replace Ubuntu's desktop environment.

To build the package from the repository root:

```bash
python3 scripts/build.py pantheon-studio --suite stonking
```

Build dependencies are listed in `packages.json`. The build runs desktop-entry,
preferences, and GTK interface tests under Xvfb.
