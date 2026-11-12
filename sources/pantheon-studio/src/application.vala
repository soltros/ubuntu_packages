public class Studio : Gtk.Application {
    private Gtk.ApplicationWindow window;
    private Gtk.ListBox list;
    private Gtk.Entry name_entry;
    private Gtk.Entry icon_entry;
    private Gtk.CheckButton hidden;
    private Gtk.Box editor;
    private Gtk.Button restore_button;
    private Gtk.Label status;
    private Gtk.Image preview;
    private DesktopAppInfo? selected;
    private OverrideStore store;
    public Studio () { Object (application_id: "io.github.soltros.PantheonStudio"); }
    protected override void activate () {
        if (window != null) { window.present (); return; }
        store = new OverrideStore (Path.build_filename (Environment.get_user_data_dir (), "applications"),
            Path.build_filename (Environment.get_user_state_dir (), "pantheon-studio", "backups"));
        var appearance = Granite.Settings.get_default ();
        Gtk.Settings.get_default ().gtk_application_prefer_dark_theme = appearance.prefers_color_scheme == Granite.Settings.ColorScheme.DARK;
        appearance.notify["prefers-color-scheme"].connect (() => {
            Gtk.Settings.get_default ().gtk_application_prefer_dark_theme = appearance.prefers_color_scheme == Granite.Settings.ColorScheme.DARK;
        });
        window = new Gtk.ApplicationWindow (this) { title = "Pantheon Studio", default_width = 850, default_height = 580 };
        window.set_titlebar (new Gtk.HeaderBar ());
        var pane = new Gtk.Paned (Gtk.Orientation.HORIZONTAL) { position = 300 };
        var pages = new Gtk.Stack ();
        var switcher = new Gtk.StackSwitcher () { stack = pages };
        ((Gtk.HeaderBar) window.get_titlebar ()).set_title_widget (switcher);
        pages.add_titled (pane, "applications", "Applications");
        pages.add_titled (new Customize (), "customize", "Desktop & Launcher");
        window.child = pages;
        var sidebar = new Gtk.Box (Gtk.Orientation.VERTICAL, 8);
        var search = new Gtk.SearchEntry () { placeholder_text = "Search applications", margin_start = 12, margin_end = 12, margin_top = 12 };
        sidebar.append (search);
        list = new Gtk.ListBox ();
        list.add_css_class ("navigation-sidebar");
        list.set_filter_func ((row) => {
            var app = row.get_data<DesktopAppInfo> ("app");
            return app.get_display_name ().casefold ().contains (search.text.casefold ());
        });
        search.search_changed.connect (() => list.invalidate_filter ());
        sidebar.append (new Gtk.ScrolledWindow () { child = list, vexpand = true, hscrollbar_policy = Gtk.PolicyType.NEVER });
        pane.start_child = sidebar;
        editor = new Gtk.Box (Gtk.Orientation.VERTICAL, 14) { margin_top = 24, margin_bottom = 24, margin_start = 24, margin_end = 24, sensitive = false };
        pane.end_child = editor;
        var title = new Gtk.Label ("Application Appearance") { xalign = 0 };
        title.add_css_class ("title-2"); editor.append (title);
        preview = new Gtk.Image () { pixel_size = 64, halign = Gtk.Align.START }; editor.append (preview);
        editor.append (new Gtk.Label ("Display name") { xalign = 0 });
        name_entry = new Gtk.Entry (); editor.append (name_entry);
        editor.append (new Gtk.Label ("Icon name or absolute file path") { xalign = 0 });
        icon_entry = new Gtk.Entry (); editor.append (icon_entry);
        icon_entry.changed.connect (() => {
            if (Path.is_absolute (icon_entry.text)) preview.set_from_file (icon_entry.text);
            else preview.set_from_icon_name (icon_entry.text);
        });
        var choose = new Gtk.Button.with_label ("Choose Icon File…"); editor.append (choose);
        choose.clicked.connect (() => {
            var dialog = new Gtk.FileChooserNative ("Choose Icon", window, Gtk.FileChooserAction.OPEN, "Select", "Cancel");
            var filter = new Gtk.FileFilter (); filter.add_pixbuf_formats (); dialog.add_filter (filter);
            dialog.response.connect ((response) => {
                if (response == Gtk.ResponseType.ACCEPT) icon_entry.text = dialog.get_file ().get_path () ?? "";
                dialog.destroy ();
            });
            dialog.show ();
        });
        hidden = new Gtk.CheckButton.with_label ("Hide from the Applications menu"); editor.append (hidden);
        var hint = new Gtk.Label ("Changes apply to your account. Restore returns the entry to its state before your first edit. Keep custom icon files in a permanent location.") { wrap = true, xalign = 0 };
        hint.add_css_class ("dim-label"); editor.append (hint);
        var actions = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 8);
        restore_button = new Gtk.Button.with_label ("Restore Defaults"); actions.append (restore_button);
        var save = new Gtk.Button.with_label ("Save Changes"); save.add_css_class ("suggested-action"); actions.append (save); editor.append (actions);
        status = new Gtk.Label ("") { wrap = true, xalign = 0, selectable = true }; editor.append (status);
        save.clicked.connect (() => change (false)); restore_button.clicked.connect (() => change (true));
        list.row_selected.connect ((row) => {
            if (row == null) { selected = null; editor.sensitive = false; return; }
            selected = row.get_data<DesktopAppInfo> ("app");
            name_entry.text = selected.get_display_name ();
            icon_entry.text = selected.get_string ("Icon") ?? "";
            hidden.active = selected.get_nodisplay ();
            restore_button.sensitive = store.managed (selected.get_id ());
            editor.sensitive = true; status.label = "";
        });
        refresh (null);
        window.present ();
    }
    private void refresh (string? select_id) {
        while (list.get_first_child () != null) list.remove (list.get_first_child ());
        var apps = new Gee.ArrayList<DesktopAppInfo> ();
        foreach (var info in AppInfo.get_all ()) {
            var app = info as DesktopAppInfo;
            if (app != null && app.get_filename () != null) apps.add (app);
        }
        apps.sort ((a, b) => a.get_display_name ().collate (b.get_display_name ()));
        foreach (var app in apps) {
            var row = new Gtk.ListBoxRow ();
            row.set_data<DesktopAppInfo> ("app", app);
            var label = new Gtk.Label (app.get_display_name ()) { xalign = 0, margin_start = 12, margin_end = 12, margin_top = 12, margin_bottom = 12, ellipsize = Pango.EllipsizeMode.END };
            row.child = label; row.tooltip_text = app.get_id (); list.append (row);
            if (app.get_id () == select_id) list.select_row (row);
        }
    }
    private void change (bool restore) {
        if (selected == null) return;
        string id = selected.get_id ();
        try {
            if (restore) store.restore (id);
            else store.save (id, selected.get_filename (), name_entry.text, icon_entry.text, hidden.active);
            refresh (id);
            status.label = restore ? "Original entry restored." : "Saved. The Applications menu may take a moment to refresh.";
        } catch (Error e) { status.label = e.message; }
    }
    public static int main (string[] args) { return new Studio ().run (args); }
}
