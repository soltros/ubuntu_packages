// SPDX-License-Identifier: GPL-3.0-or-later
private Gtk.Widget? find_folder (Gtk.Widget widget) {
    if (widget is Slingshot.Widgets.StudioFolder) return widget;
    if (widget is Gtk.Container) {
        foreach (var child in ((Gtk.Container) widget).get_children ()) {
            var found = find_folder (child); if (found != null) return found;
        }
    }
    return null;
}
void main (string[] args) {
    try {
        string root = DirUtils.make_tmp ("studio-launcher-XXXXXX");
        Environment.set_variable ("XDG_CONFIG_HOME", root, true);
        Environment.set_variable ("XDG_DATA_HOME", root, true);
        Environment.set_variable ("GSETTINGS_BACKEND", "memory", true);
        DirUtils.create_with_parents (Path.build_filename (root, "applications"), 0700);
        FileUtils.set_contents (Path.build_filename (root, "applications", "studio-test.desktop"), "[Desktop Entry]\nType=Application\nName=Studio Fixture\nExec=true\nIcon=utilities-terminal\n");
        var prefs = new StudioPreferences ();
        prefs.key.set_string ("Folder test", "name", "Test Folder");
        prefs.assign ("studio-test.desktop", "Folder test"); prefs.save ();
        Gtk.init (ref args);
        var window = new Gtk.Window () { default_width = 900, default_height = 600 };
        var view = new Slingshot.SlingshotView (); window.add (view); window.show_all ();
        view.show_slingshot ();
        var folder = find_folder (view); assert (folder != null);
        ((Gtk.Button) folder).clicked ();
        while (MainContext.default ().pending ()) MainContext.default ().iteration (false);
        prefs.key.remove_group ("Folder test"); prefs.save ();
        view.show_slingshot (); assert (find_folder (view) == null);
        window.destroy ();
    } catch (Error e) { error ("Launcher test: %s", e.message); }
}
