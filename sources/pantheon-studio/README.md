# Pantheon Studio

A native Vala, GTK 4, and Granite application for editing application display names,
icons, and menu visibility. Search the application list, select an entry, edit its
fields, and choose Save Changes. Hidden entries remain in the editor so they can
be shown again. Unsaved edits are discarded when selecting another application.

## Build and run

```sh
nix build .#pantheon-studio
nix run .#pantheon-studio
```

The flake exposes the package for x86_64-linux and aarch64-linux and through
`overlays.default`. Add `pkgs.pantheon-studio` to `environment.systemPackages`
when using the overlay. The build runs isolated desktop-entry roundtrip tests.

## Storage and restoration

Overrides live in `$XDG_DATA_HOME/applications` (normally
`~/.local/share/applications`). Recovery records live in
`$XDG_STATE_HOME/pantheon-studio/backups` (normally
`~/.local/state/pantheon-studio/backups`). Keep these records until you restore
changes. Restore Defaults restores the exact pre-edit local file, or removes
our override when there was no local file, exposing the current system entry.
Uninstalling the app does not remove overrides; restore them first if desired.

Executable commands, desktop actions, and unrelated keys are preserved. Custom
names replace translated Name fields in the override; restoration recovers them.
Custom icon files are referenced in place and should remain at their chosen path.
Edits may also appear in other launchers or docks that read desktop entries.

Nix-managed symlinks are rejected. Changes made outside this app are detected
before subsequent saves or restoration. If a conflict occurs, review the desktop
file and its recovery record manually; the app does not force an overwrite.
User overrides can mask future upstream desktop-entry changes until restored.

## Launcher, folders, panel, and desktop controls

Version 0.2 adds:

- Desktop icon-theme selection. The patched Wingpanel removes its hardcoded
  elementary icon theme, so the launcher follows the desktop selection.
- Launcher folders with names, icons, and application membership. Nonempty folders
  appear before ungrouped applications in grid view. Apps remain searchable and
  available in category view. Removing a folder returns its apps to the main grid.
- Launcher button label/icon, optional label visibility, grid rows/columns, and
  application icon size. Grid changes apply when the launcher next opens.
- Panel background/text colors, opacity, minimum height, and indicator padding,
  with live reload and restoration of the standard appearance.
- Desktop animation, touchpad scrolling/tap-to-click, window centering, and panel
  workspace-scrolling switches when their settings are available.

Folder and layout settings live in `$XDG_CONFIG_HOME/pantheon-studio/desktop.ini`.
Desktop switches and icon-theme selection use the existing desktop GSettings.
Icon themes must be installed and discoverable in the desktop session. Absolute
per-application icon overrides still take precedence over icon-theme selection.
The module also lets panel indicator icons follow the selected icon theme.

### Enable the desktop integration on NixOS

Installing Studio alone provides the editor and desktop settings. Launcher folders,
launcher-button changes, the icon-theme fix, and panel appearance need the companion
components. Import the module from this flake in your NixOS configuration:

```nix
{
  imports = [ inputs.soltros-nixpkgs.nixosModules.pantheon-studio ];
  programs.pantheon-studio.enable = true;
}
```

Use your own input name if it differs. Pantheon must already be enabled. The module
installs Studio and overrides the launcher and panel used by the standard NixOS
Pantheon session; adding the standalone companion packages to systemPackages is
not sufficient. Update your flake input, rebuild NixOS, then log out and back in
once. Subsequent customization changes require no rebuild.

The integrations currently target Wingpanel and Applications Menu 8.0.4 (GTK 3).
An explicit version check prevents applying these patches to an incompatible
upstream release. Studio itself remains GTK 4. Disabling the module and rebuilding
restores the stock components; your saved settings remain available.

Nested folders, drag-and-drop folder editing, arbitrary indicator reordering,
panel positioning/autohide, and full GTK theme replacement are not implemented.
Panel height is a minimum; upstream layout can enforce a larger height.

### Validation

The Studio build runs desktop-entry, folder-membership, and GTK 4 interface tests.
The launcher build runs upstream tests and a GTK 3 folder integration test under
Xvfb. Flake checks verify that the NixOS module selects the patched panel and
launcher. Runtime GUI tests use temporary settings and do not alter your session.
