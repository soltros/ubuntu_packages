private Gtk.Button? find_button (Gtk.Widget widget, string label) {
    if (widget is Gtk.Button && ((Gtk.Button) widget).label == label) return (Gtk.Button) widget;
    for (var child = widget.get_first_child (); child != null; child = child.get_next_sibling ()) {
        var found = find_button (child, label);
        if (found != null) return found;
    }
    return null;
}
void main (string[] args) {
    try {
        Environment.set_variable ("XDG_CONFIG_HOME", DirUtils.make_tmp ("studio-ui-XXXXXX"), true);
        Environment.set_variable ("GSETTINGS_BACKEND", "memory", true);
        Gtk.init ();
        var window = new Gtk.Window () { default_width = 850, default_height = 650 };
        var view = new Customize (); window.child = view; window.present ();
        while (MainContext.default ().pending ()) MainContext.default ().iteration (false);
        var create = find_button (view, "New Folder"); assert (create != null); create.clicked ();
        var prefs = StudioPreferences.current (); assert (prefs.folders ().length == 1);
        var save = find_button (view, "Save Folder"); assert (save != null); save.clicked ();
        var remove = find_button (view, "Remove Folder"); assert (remove != null); remove.clicked ();
        prefs = StudioPreferences.current (); assert (prefs.folders ().length == 0);
        find_button (view, "Apply Launcher Settings").clicked ();
        prefs = StudioPreferences.current (); assert (prefs.key.has_group ("Launcher"));
        find_button (view, "Restore Launcher Defaults").clicked ();
        prefs = StudioPreferences.current (); assert (!prefs.key.has_group ("Launcher"));
        find_button (view, "Apply Panel Settings").clicked ();
        prefs = StudioPreferences.current (); assert (prefs.key.has_group ("Panel"));
        find_button (view, "Restore Panel Appearance").clicked ();
        prefs = StudioPreferences.current (); assert (!prefs.key.has_group ("Panel"));
        window.destroy ();
    } catch (Error e) { error ("UI test failed: %s", e.message); }
}
