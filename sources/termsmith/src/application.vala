using Gtk;

public class TerminalProfile : Object {
    public string id { get; set; }
    public string name { get; set; }
    public string directory { get; set; }
    public string command { get; set; }
    public string icon { get; set; }

    public TerminalProfile (string id, string name, string directory, string command, string icon) {
        this.id = id;
        this.name = name;
        this.directory = directory;
        this.command = command;
        this.icon = icon;
    }
}

public class TermsmithApp : Gtk.Application {
    private const string APP_ID = "io.github.derrik.Termsmith";
    private const string DEFAULT_COMMAND = "exec ${SHELL:-zsh}";
    private const string DEFAULT_ICON = "utilities-terminal";

    private Gtk.ApplicationWindow? window;
    private Gtk.ListBox profile_list;
    private Gtk.Entry name_entry;
    private Gtk.Entry directory_entry;
    private Gtk.Entry command_entry;
    private Gtk.Button icon_button;
    private Gtk.Image icon_preview;
    private Gtk.Label icon_name_label;
    private string selected_icon = DEFAULT_ICON;
    private Gtk.Button save_button;
    private Gtk.Button launch_button;
    private Gtk.Button shortcut_button;
    private Gtk.Button delete_button;
    private Gee.ArrayList<TerminalProfile> profiles = new Gee.ArrayList<TerminalProfile> ();
    private TerminalProfile? selected_profile;

    private const OptionEntry[] OPTIONS = {
        { "launch", 0, 0, OptionArg.STRING, null, "Launch a saved profile", "PROFILE_ID" },
        { null }
    };

    public TermsmithApp () {
        Object (application_id: APP_ID, flags: ApplicationFlags.HANDLES_COMMAND_LINE);
        add_main_option_entries (OPTIONS);
    }

    public override int command_line (ApplicationCommandLine command_line) {
        activate ();
        var launch_option = command_line.get_options_dict ().lookup_value (
            "launch",
            VariantType.STRING
        );
        if (launch_option != null) {
            var launch_id = launch_option.get_string ();
            load_profiles ();
            foreach (var profile in profiles) {
                if (profile.id == launch_id) {
                    launch_profile (profile);
                    if (window != null) window.close ();
                    return 0;
                }
            }
            warning ("No terminal profile named %s", launch_id);
            return 1;
        }
        return 0;
    }

    protected override void activate () {
        if (window != null) {
            window.present ();
            return;
        }

        follow_system_appearance ();
        build_window ();
        load_profiles ();
        refresh_profile_list ();
        window.present ();
    }

    private void follow_system_appearance () {
        var granite_settings = Granite.Settings.get_default ();
        var gtk_settings = Gtk.Settings.get_default ();
        if (gtk_settings == null) return;

        update_color_scheme (granite_settings, gtk_settings);
        granite_settings.notify["prefers-color-scheme"].connect (() => {
            update_color_scheme (granite_settings, gtk_settings);
        });
    }

    private void update_color_scheme (Granite.Settings granite_settings, Gtk.Settings gtk_settings) {
        gtk_settings.gtk_application_prefer_dark_theme =
            granite_settings.prefers_color_scheme == Granite.Settings.ColorScheme.DARK;
    }

    private void build_window () {
        window = new Gtk.ApplicationWindow (this) {
            title = "Termsmith",
            default_width = 780,
            default_height = 500
        };

        var header = new Gtk.HeaderBar ();
        var add_button = new Gtk.Button.from_icon_name ("list-add-symbolic") {
            tooltip_text = "New Profile"
        };
        add_button.clicked.connect (new_profile);
        header.pack_start (add_button);
        window.set_titlebar (header);

        var paned = new Gtk.Paned (Gtk.Orientation.HORIZONTAL) {
            position = 250,
            shrink_start_child = false,
            shrink_end_child = false
        };
        window.child = paned;

        profile_list = new Gtk.ListBox () {
            selection_mode = Gtk.SelectionMode.SINGLE
        };
        profile_list.add_css_class ("navigation-sidebar");
        profile_list.row_selected.connect (profile_selected);
        var sidebar_scroll = new Gtk.ScrolledWindow () {
            child = profile_list,
            hscrollbar_policy = Gtk.PolicyType.NEVER
        };
        sidebar_scroll.set_size_request (220, -1);
        paned.start_child = sidebar_scroll;

        var editor = new Gtk.Box (Gtk.Orientation.VERTICAL, 18) {
            margin_top = 30,
            margin_bottom = 30,
            margin_start = 30,
            margin_end = 30,
            valign = Gtk.Align.START
        };
        paned.end_child = editor;

        var title = new Gtk.Label ("Terminal Profile") {
            xalign = 0
        };
        title.add_css_class ("title-2");
        editor.append (title);

        var grid = new Gtk.Grid () {
            row_spacing = 12,
            column_spacing = 12
        };
        editor.append (grid);

        name_entry = add_field (grid, 0, "Name", "Project Shell");
        directory_entry = add_field (grid, 1, "Working Folder", Environment.get_home_dir ());
        command_entry = add_field (grid, 2, "Startup Command", DEFAULT_COMMAND);
        add_icon_field (grid, 3);

        var hint = new Gtk.Label ("The command runs through your login shell. Leave it blank to open a normal shell.") {
            xalign = 0,
            wrap = true
        };
        hint.add_css_class ("dim-label");
        editor.append (hint);

        var actions = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 9) {
            margin_top = 12,
            halign = Gtk.Align.END
        };
        editor.append (actions);

        delete_button = new Gtk.Button.with_label ("Delete");
        delete_button.add_css_class ("destructive-action");
        delete_button.clicked.connect (delete_selected);
        actions.append (delete_button);

        shortcut_button = new Gtk.Button.with_label ("Create Shortcut");
        shortcut_button.clicked.connect (create_shortcut);
        actions.append (shortcut_button);

        launch_button = new Gtk.Button.with_label ("Launch");
        launch_button.clicked.connect (() => save_and_launch ());
        actions.append (launch_button);

        save_button = new Gtk.Button.with_label ("Save");
        save_button.add_css_class ("suggested-action");
        save_button.clicked.connect (save_selected);
        actions.append (save_button);

        set_editor_sensitive (false);
    }

    private Gtk.Entry add_field (Gtk.Grid grid, int row, string label_text, string placeholder) {
        var label = new Gtk.Label (label_text) {
            xalign = 1,
            valign = Gtk.Align.CENTER
        };
        var entry = new Gtk.Entry () {
            hexpand = true,
            placeholder_text = placeholder
        };
        grid.attach (label, 0, row, 1, 1);
        grid.attach (entry, 1, row, 1, 1);
        return entry;
    }

    private void add_icon_field (Gtk.Grid grid, int row) {
        var label = new Gtk.Label ("Icon") {
            xalign = 1,
            valign = Gtk.Align.CENTER
        };
        icon_preview = new Gtk.Image.from_icon_name (DEFAULT_ICON) {
            pixel_size = 32
        };
        icon_name_label = new Gtk.Label (DEFAULT_ICON) {
            xalign = 0,
            hexpand = true,
            ellipsize = Pango.EllipsizeMode.END
        };
        var content = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 9) {
            margin_top = 4,
            margin_bottom = 4,
            margin_start = 6,
            margin_end = 6
        };
        content.append (icon_preview);
        content.append (icon_name_label);
        icon_button = new Gtk.Button () {
            child = content,
            hexpand = true,
            tooltip_text = "Browse installed icons"
        };
        icon_button.clicked.connect (open_icon_browser);
        grid.attach (label, 0, row, 1, 1);
        grid.attach (icon_button, 1, row, 1, 1);
    }

    private void set_selected_icon (string icon_name) {
        selected_icon = icon_name.length > 0 ? icon_name : DEFAULT_ICON;
        icon_preview.set_from_icon_name (selected_icon);
        icon_name_label.label = selected_icon;
    }

    private void open_icon_browser () {
        var dialog = new Gtk.Window () {
            title = "Choose an Icon",
            default_width = 680,
            default_height = 540,
            modal = true,
            transient_for = window
        };

        var header = new Gtk.HeaderBar ();
        dialog.set_titlebar (header);

        var search = new Gtk.SearchEntry () {
            placeholder_text = "Search icons…",
            margin_top = 12,
            margin_bottom = 12,
            margin_start = 12,
            margin_end = 12
        };
        var flow = new Gtk.FlowBox () {
            selection_mode = Gtk.SelectionMode.NONE,
            homogeneous = true,
            min_children_per_line = 3,
            max_children_per_line = 6,
            column_spacing = 6,
            row_spacing = 6,
            margin_bottom = 12,
            margin_start = 12,
            margin_end = 12
        };

        var display = Gdk.Display.get_default ();
        if (display != null) {
            var icon_theme = Gtk.IconTheme.get_for_display (display);
            foreach (var icon_name in icon_theme.get_icon_names ()) {
                var chosen_icon = icon_name;
                var image = new Gtk.Image.from_icon_name (chosen_icon) {
                    pixel_size = 48
                };
                var name = new Gtk.Label (chosen_icon) {
                    ellipsize = Pango.EllipsizeMode.END,
                    max_width_chars = 13,
                    xalign = 0.5f
                };
                var box = new Gtk.Box (Gtk.Orientation.VERTICAL, 6) {
                    margin_top = 8,
                    margin_bottom = 8,
                    margin_start = 6,
                    margin_end = 6
                };
                box.append (image);
                box.append (name);
                var button = new Gtk.Button () {
                    child = box,
                    tooltip_text = chosen_icon
                };
                button.set_data<string> ("icon-name", chosen_icon);
                button.clicked.connect (() => {
                    set_selected_icon (chosen_icon);
                    dialog.close ();
                });
                flow.append (button);
            }
        }

        flow.set_filter_func ((child) => {
            var button = child.get_child () as Gtk.Button;
            if (button == null) return false;
            var icon_name = button.get_data<string> ("icon-name");
            var query = search.text.strip ().down ();
            return query.length == 0 || icon_name.down ().contains (query);
        });
        search.search_changed.connect (() => flow.invalidate_filter ());

        var scroll = new Gtk.ScrolledWindow () {
            child = flow,
            vexpand = true,
            hscrollbar_policy = Gtk.PolicyType.NEVER
        };
        var content = new Gtk.Box (Gtk.Orientation.VERTICAL, 0);
        content.append (search);
        content.append (scroll);
        dialog.child = content;
        dialog.present ();
        search.grab_focus ();
    }

    private string config_path () {
        return Path.build_filename (Environment.get_user_config_dir (), "termsmith", "profiles.ini");
    }

    private void load_profiles () {
        profiles.clear ();
        var key_file = new KeyFile ();
        try {
            key_file.load_from_file (config_path (), KeyFileFlags.NONE);
            foreach (var group in key_file.get_groups ()) {
                profiles.add (new TerminalProfile (
                    group,
                    key_file.get_string (group, "name"),
                    key_file.get_string (group, "directory"),
                    key_file.get_string (group, "command"),
                    key_file.has_key (group, "icon") ? key_file.get_string (group, "icon") : DEFAULT_ICON
                ));
            }
        } catch (Error error) {
            if (!(error is FileError.NOENT)) warning ("Unable to load profiles: %s", error.message);
        }
    }

    private void save_profiles () {
        var key_file = new KeyFile ();
        foreach (var profile in profiles) {
            key_file.set_string (profile.id, "name", profile.name);
            key_file.set_string (profile.id, "directory", profile.directory);
            key_file.set_string (profile.id, "command", profile.command);
            key_file.set_string (profile.id, "icon", profile.icon);
        }

        var directory = Path.get_dirname (config_path ());
        try {
            DirUtils.create_with_parents (directory, 0700);
            FileUtils.set_contents (config_path (), key_file.to_data ());
        } catch (Error error) {
            show_error ("Couldn’t save profiles", error.message);
        }
    }

    private void refresh_profile_list () {
        while (profile_list.get_first_child () != null) {
            profile_list.remove (profile_list.get_first_child ());
        }
        foreach (var profile in profiles) {
            var row = new Gtk.ListBoxRow ();
            row.set_data<string> ("profile-id", profile.id);
            var icon = new Gtk.Image.from_icon_name (profile.icon) {
                pixel_size = 32
            };
            var label = new Gtk.Label (profile.name) {
                xalign = 0,
                hexpand = true,
                ellipsize = Pango.EllipsizeMode.END
            };
            var content = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 10) {
                margin_top = 10,
                margin_bottom = 10,
                margin_start = 12,
                margin_end = 12
            };
            content.append (icon);
            content.append (label);
            row.child = content;
            profile_list.append (row);
        }
    }

    private void new_profile () {
        var id = Uuid.string_random ();
        var profile = new TerminalProfile (id, "New Profile", Environment.get_home_dir (), "", DEFAULT_ICON);
        profiles.add (profile);
        save_profiles ();
        refresh_profile_list ();
        select_profile_by_id (id);
        name_entry.grab_focus ();
        name_entry.select_region (0, -1);
    }

    private void profile_selected (Gtk.ListBoxRow? row) {
        if (row == null) return;
        var id = row.get_data<string> ("profile-id");
        foreach (var profile in profiles) {
            if (profile.id == id) {
                selected_profile = profile;
                name_entry.text = profile.name;
                directory_entry.text = profile.directory;
                command_entry.text = profile.command;
                set_selected_icon (profile.icon);
                set_editor_sensitive (true);
                return;
            }
        }
    }

    private void select_profile_by_id (string id) {
        var child = profile_list.get_first_child ();
        while (child != null) {
            var row = child as Gtk.ListBoxRow;
            if (row != null && row.get_data<string> ("profile-id") == id) {
                profile_list.select_row (row);
                return;
            }
            child = child.get_next_sibling ();
        }
    }

    private void save_selected () {
        if (selected_profile == null) return;
        selected_profile.name = name_entry.text.strip ().length > 0 ? name_entry.text.strip () : "Unnamed Profile";
        selected_profile.directory = directory_entry.text.strip ().length > 0 ? directory_entry.text.strip () : Environment.get_home_dir ();
        selected_profile.command = command_entry.text;
        selected_profile.icon = selected_icon;
        save_profiles ();
        var id = selected_profile.id;
        refresh_profile_list ();
        select_profile_by_id (id);
    }

    private void save_and_launch () {
        save_selected ();
        if (selected_profile != null) launch_profile (selected_profile);
    }

    private void launch_profile (TerminalProfile profile) {
        if (!FileUtils.test (profile.directory, FileTest.IS_DIR)) {
            show_error ("Working folder doesn’t exist", profile.directory);
            return;
        }

        var shell = Environment.get_variable ("SHELL") ?? "/bin/sh";
        var command = profile.command.strip ();
        if (command.length == 0) command = "exec " + Shell.quote (shell);

        string[] argv = {
            "alacritty",
            "--working-directory", profile.directory,
            "--title", profile.name,
            "-e", shell, "-lc", command
        };

        try {
            new Subprocess.newv (argv, SubprocessFlags.NONE);
        } catch (Error error) {
            show_error ("Couldn’t launch Alacritty", error.message);
        }
    }

    private void create_shortcut () {
        save_selected ();
        if (selected_profile == null) return;

        var applications = Path.build_filename (Environment.get_user_data_dir (), "applications");
        var filename = "termsmith-" + selected_profile.id + ".desktop";
        var path = Path.build_filename (applications, filename);
        var desktop = "[Desktop Entry]\n" +
            "Name=" + desktop_escape (selected_profile.name) + "\n" +
            "Comment=Launch " + desktop_escape (selected_profile.name) + " terminal profile\n" +
            "Exec=termsmith --launch " + selected_profile.id + "\n" +
            "Icon=" + desktop_escape (selected_profile.icon) + "\n" +
            "Terminal=false\nType=Application\nCategories=System;TerminalEmulator;\n";
        try {
            DirUtils.create_with_parents (applications, 0755);
            FileUtils.set_contents (path, desktop);
            show_message ("Shortcut created", "“%s” is now available in the Applications menu.".printf (selected_profile.name));
        } catch (Error error) {
            show_error ("Couldn’t create shortcut", error.message);
        }
    }

    private string desktop_escape (string value) {
        return value.replace ("\\", "\\\\").replace ("\n", "\\n");
    }

    private void delete_selected () {
        if (selected_profile == null) return;
        profiles.remove (selected_profile);
        selected_profile = null;
        save_profiles ();
        refresh_profile_list ();
        name_entry.text = "";
        directory_entry.text = "";
        command_entry.text = "";
        set_selected_icon (DEFAULT_ICON);
        set_editor_sensitive (false);
    }

    private void set_editor_sensitive (bool sensitive) {
        name_entry.sensitive = sensitive;
        directory_entry.sensitive = sensitive;
        command_entry.sensitive = sensitive;
        icon_button.sensitive = sensitive;
        save_button.sensitive = sensitive;
        launch_button.sensitive = sensitive;
        shortcut_button.sensitive = sensitive;
        delete_button.sensitive = sensitive;
    }

    private void show_error (string title, string detail) {
        show_message (title, detail);
    }

    private void show_message (string title, string detail) {
        var dialog = new Gtk.AlertDialog (title) {
            detail = detail
        };
        dialog.show (window);
    }

    public static int main (string[] args) {
        return new TermsmithApp ().run (args);
    }
}
