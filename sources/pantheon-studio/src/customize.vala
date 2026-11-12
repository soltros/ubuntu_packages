// SPDX-License-Identifier: GPL-3.0-or-later
public class Customize : Gtk.Box {
    private Gtk.Label status;
    private Gtk.ComboBoxText folders;
    private Gtk.Entry folder_name;
    private Gtk.Entry folder_icon;
    private Gtk.ListBox members;
    private bool loading = false;
    public Customize () {
        Object (orientation: Gtk.Orientation.VERTICAL, spacing: 12, margin_top: 16, margin_bottom: 16, margin_start: 20, margin_end: 20);
        var notebook = new Gtk.Notebook () { vexpand = true };
        append (notebook);
        status = new Gtk.Label ("") { xalign = 0, wrap = true, selectable = true }; append (status);
        notebook.append_page (launcher_page (), new Gtk.Label ("Launcher"));
        notebook.append_page (folder_page (), new Gtk.Label ("Folders"));
        notebook.append_page (panel_page (), new Gtk.Label ("Panel"));
        notebook.append_page (desktop_page (), new Gtk.Label ("Desktop"));
        var hint = new Gtk.Label ("Launcher folders, button controls, and panel appearance require the Pantheon Studio NixOS module. After enabling it, log out and back in once.") { wrap = true, xalign = 0 };
        hint.add_css_class ("dim-label"); append (hint);
    }
    private Gtk.Box form () { return new Gtk.Box (Gtk.Orientation.VERTICAL, 12) { margin_top = 18, margin_bottom = 18, margin_start = 18, margin_end = 18 }; }
    private Gtk.Widget scroll (Gtk.Widget child) { return new Gtk.ScrolledWindow () { child = child, hscrollbar_policy = Gtk.PolicyType.NEVER }; }
    private Gtk.Entry entry (Gtk.Box box, string title, string value) {
        box.append (new Gtk.Label (title) { xalign = 0 });
        var field = new Gtk.Entry () { text = value }; box.append (field); return field;
    }
    private Gtk.SpinButton spin (Gtk.Box box, string title, int value, int min, int max) {
        var row = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 12);
        row.append (new Gtk.Label (title) { xalign = 0, hexpand = true });
        var field = new Gtk.SpinButton.with_range (min, max, 1) { value = value }; row.append (field); box.append (row); return field;
    }
    private Gtk.Button button (Gtk.Box box, string text) { var b = new Gtk.Button.with_label (text); box.append (b); return b; }
    private void save (StudioPreferences prefs, string message) {
        try { prefs.save (); status.label = message; } catch (Error e) { status.label = e.message; }
    }
    private Gtk.Widget launcher_page () {
        var box = form (); var prefs = StudioPreferences.current ();
        box.append (new Gtk.Label ("The integrated panel follows your desktop icon theme, including the launcher. Choose your icon theme on the Desktop tab.") { wrap = true, xalign = 0 });
        var label = entry (box, "Launcher button label", prefs.text ("Launcher", "label", "Applications"));
        var icon = entry (box, "Launcher button icon name", prefs.text ("Launcher", "icon", "system-search-symbolic"));
        var show_label = new Gtk.CheckButton.with_label ("Show launcher button label") { active = prefs.flag ("Launcher", "show-label", true) }; box.append (show_label);
        var rows = spin (box, "Grid rows", prefs.number ("Launcher", "rows", 3, 2, 6), 2, 6);
        var columns = spin (box, "Grid columns", prefs.number ("Launcher", "columns", 5, 3, 8), 3, 8);
        var size = spin (box, "Application icon size", prefs.number ("Launcher", "icon-size", 64, 24, 96), 24, 96);
        button (box, "Apply Launcher Settings").clicked.connect (() => {
            var current = StudioPreferences.current ();
            current.key.set_string ("Launcher", "label", label.text);
            current.key.set_string ("Launcher", "icon", icon.text);
            current.key.set_boolean ("Launcher", "show-label", show_label.active);
            current.key.set_integer ("Launcher", "rows", rows.get_value_as_int ());
            current.key.set_integer ("Launcher", "columns", columns.get_value_as_int ());
            current.key.set_integer ("Launcher", "icon-size", size.get_value_as_int ());
            save (current, "Saved. Reopen the launcher to see its updated grid.");
        });
        button (box, "Restore Launcher Defaults").clicked.connect (() => {
            var current = StudioPreferences.current ();
            try { current.key.remove_group ("Launcher"); } catch (Error e) {}
            save (current, "Launcher defaults restored.");
            label.text = "Applications"; icon.text = "system-search-symbolic"; show_label.active = true;
            rows.value = 3; columns.value = 5; size.value = 64;
        });
        return scroll (box);
    }
    private Gtk.Widget panel_page () {
        var box = form (); var prefs = StudioPreferences.current ();
        var custom = new Gtk.CheckButton.with_label ("Use custom panel appearance") { active = prefs.flag ("Panel", "custom") }; box.append (custom);
        var bg = entry (box, "Background color (#RRGGBB)", prefs.text ("Panel", "background", "#242424"));
        var fg = entry (box, "Text and symbolic icon color (#RRGGBB)", prefs.text ("Panel", "foreground", "#ffffff"));
        var opacity = spin (box, "Background opacity (%)", prefs.number ("Panel", "opacity", 90, 0, 100), 0, 100);
        var height = spin (box, "Minimum panel height (px)", prefs.number ("Panel", "height", 30, 30, 64), 30, 64);
        var spacing = spin (box, "Indicator horizontal padding (px)", prefs.number ("Panel", "spacing", 6, 0, 24), 0, 24);
        button (box, "Apply Panel Settings").clicked.connect (() => {
            if (!Regex.match_simple ("^#[0-9a-fA-F]{6}$", bg.text) || !Regex.match_simple ("^#[0-9a-fA-F]{6}$", fg.text)) {
                status.label = "Use six-digit colors such as #242424."; return;
            }
            var current = StudioPreferences.current ();
            current.key.set_boolean ("Panel", "custom", custom.active);
            current.key.set_string ("Panel", "background", bg.text);
            current.key.set_string ("Panel", "foreground", fg.text);
            current.key.set_integer ("Panel", "opacity", opacity.get_value_as_int ());
            current.key.set_integer ("Panel", "height", height.get_value_as_int ());
            current.key.set_integer ("Panel", "spacing", spacing.get_value_as_int ());
            save (current, "Panel settings saved.");
        });
        button (box, "Restore Panel Appearance").clicked.connect (() => {
            var current = StudioPreferences.current ();
            try { current.key.remove_group ("Panel"); } catch (Error e) {}
            save (current, "Standard panel appearance restored.");
            custom.active = false; bg.text = "#242424"; fg.text = "#ffffff"; opacity.value = 90; height.value = 30; spacing.value = 6;
        });
        setting_switch (box, "Scroll over panel to switch workspaces", "io.elementary.desktop.wingpanel", "scroll-to-switch-workspaces");
        return scroll (box);
    }
    private GLib.Settings? settings (string schema_id, string key) {
        var source = SettingsSchemaSource.get_default ();
        if (source == null) return null;
        var schema = source.lookup (schema_id, true);
        if (schema == null || !schema.has_key (key)) return null;
        return new GLib.Settings.full (schema, null, null);
    }
    private void setting_switch (Gtk.Box box, string title, string schema, string key) {
        var field = new Gtk.CheckButton.with_label (title); box.append (field);
        var setting = settings (schema, key);
        if (setting == null) { field.sensitive = false; field.tooltip_text = "Unavailable in this Pantheon version"; return; }
        setting.bind (key, field, "active", SettingsBindFlags.DEFAULT);
    }
    private Gtk.Widget desktop_page () {
        var box = form ();
        box.append (new Gtk.Label ("These settings apply across your desktop immediately.") { xalign = 0, wrap = true });
        var setting = settings ("org.gnome.desktop.interface", "icon-theme");
        var themes = new Gtk.ComboBoxText ();
        var names = new Gee.TreeSet<string> ();
        names.add ("elementary"); names.add ("Adwaita");
        if (setting != null) names.add (setting.get_string ("icon-theme"));
        string[] roots = { Path.build_filename (Environment.get_home_dir (), ".icons"), Path.build_filename (Environment.get_user_data_dir (), "icons") };
        foreach (var dir in Environment.get_system_data_dirs ()) roots += Path.build_filename (dir, "icons");
        foreach (var root in roots) {
            try {
                var dir = Dir.open (root); string? name;
                while ((name = dir.read_name ()) != null) {
                    if (FileUtils.test (Path.build_filename (root, name, "index.theme"), FileTest.EXISTS)) names.add (name);
                }
            } catch (Error e) {}
        }
        box.append (new Gtk.Label ("Desktop icon theme") { xalign = 0 }); box.append (themes);
        foreach (var name in names) themes.append (name, name);
        if (setting != null) {
            themes.active_id = setting.get_string ("icon-theme");
            themes.sensitive = setting.is_writable ("icon-theme");
            themes.changed.connect (() => { if (themes.active_id != null) setting.set_string ("icon-theme", themes.active_id); });
            setting.changed["icon-theme"].connect (() => themes.active_id = setting.get_string ("icon-theme"));
            button (box, "Reset Icon Theme").clicked.connect (() => setting.reset ("icon-theme"));
        } else themes.sensitive = false;
        setting_switch (box, "Enable animations", "org.gnome.desktop.interface", "enable-animations");
        setting_switch (box, "Natural scrolling (touchpad)", "org.gnome.desktop.peripherals.touchpad", "natural-scroll");
        setting_switch (box, "Tap to click", "org.gnome.desktop.peripherals.touchpad", "tap-to-click");
        setting_switch (box, "Center new windows", "org.gnome.mutter", "center-new-windows");
        return scroll (box);
    }
    private Gtk.Widget folder_page () {
        var box = form ();
        box.append (new Gtk.Label ("Folders appear in the launcher grid. Apps remain searchable. Each app belongs to at most one folder. Membership changes save immediately.") { wrap = true, xalign = 0 });
        folders = new Gtk.ComboBoxText (); box.append (folders);
        folder_name = entry (box, "Folder name", ""); folder_icon = entry (box, "Folder icon name", "folder");
        var actions = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 8); box.append (actions);
        button (actions, "New Folder").clicked.connect (() => {
            var prefs = StudioPreferences.current (); var id = "Folder " + Uuid.string_random ();
            prefs.key.set_string (id, "name", "New Folder"); prefs.key.set_string (id, "icon", "folder");
            save (prefs, "Folder created."); refresh_folders (id);
        });
        button (actions, "Save Folder").clicked.connect (() => {
            if (folders.active_id == null || folder_name.text.strip () == "") { status.label = "Select a folder and enter its name."; return; }
            var prefs = StudioPreferences.current (); string id = folders.active_id;
            prefs.key.set_string (id, "name", folder_name.text.strip ()); prefs.key.set_string (id, "icon", folder_icon.text.strip ());
            save (prefs, "Folder saved."); refresh_folders (id);
        });
        button (actions, "Remove Folder").clicked.connect (() => {
            if (folders.active_id == null) return;
            var prefs = StudioPreferences.current ();
            try { prefs.key.remove_group (folders.active_id); } catch (Error e) { status.label = e.message; return; }
            save (prefs, "Folder removed. Its apps return to the main grid."); refresh_folders (null);
        });
        var search = new Gtk.SearchEntry () { placeholder_text = "Find apps to add" }; box.append (search);
        members = new Gtk.ListBox () { selection_mode = Gtk.SelectionMode.NONE };
        members.set_filter_func ((row) => ((Gtk.CheckButton) row.child).label.casefold ().contains (search.text.casefold ()));
        search.search_changed.connect (() => members.invalidate_filter ());
        box.append (new Gtk.ScrolledWindow () { child = members, vexpand = true, min_content_height = 160 });
        folders.changed.connect (load_members); refresh_folders (null);
        return scroll (box);
    }
    private void refresh_folders (string? id) {
        loading = true; folders.remove_all ();
        var prefs = StudioPreferences.current ();
        foreach (var group in prefs.folders ()) folders.append (group, prefs.text (group, "name", "Folder"));
        if (id != null) folders.active_id = id; else folders.active = 0;
        loading = false; load_members ();
    }
    private void load_members () {
        if (loading) return;
        while (members.get_first_child () != null) members.remove (members.get_first_child ());
        string? id = folders.active_id;
        folder_name.sensitive = folder_icon.sensitive = id != null;
        if (id == null) { folder_name.text = ""; folder_icon.text = "folder"; return; }
        var prefs = StudioPreferences.current ();
        folder_name.text = prefs.text (id, "name", "Folder"); folder_icon.text = prefs.text (id, "icon", "folder");
        var apps = new Gee.ArrayList<AppInfo> ();
        foreach (var app in AppInfo.get_all ()) if (app.should_show ()) apps.add (app);
        apps.sort ((a, b) => a.get_display_name ().collate (b.get_display_name ()));
        foreach (var app in apps) {
            var check = new Gtk.CheckButton.with_label (app.get_display_name ()) { active = app.get_id () in prefs.members (id) };
            check.tooltip_text = app.get_id ();
            check.toggled.connect (() => {
                var current = StudioPreferences.current ();
                current.assign (app.get_id (), check.active ? id : null);
                save (current, "Folder membership saved. Reopen the launcher to refresh.");
            });
            members.append (check);
        }
    }
}
