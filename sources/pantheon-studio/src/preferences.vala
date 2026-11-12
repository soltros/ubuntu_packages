// SPDX-License-Identifier: GPL-3.0-or-later
// Shared configuration for the GTK 4 editor and GTK 3 desktop integrations.
public class StudioPreferences : Object {
    public KeyFile key = new KeyFile ();
    public string path;
    public StudioPreferences (string? path = null) {
        this.path = path ?? Path.build_filename (Environment.get_user_config_dir (), "pantheon-studio", "desktop.ini");
    }
    public void load () throws Error {
        key = new KeyFile ();
        if (FileUtils.test (path, FileTest.EXISTS)) key.load_from_file (path, KeyFileFlags.NONE);
    }
    public void save () throws Error {
        if (DirUtils.create_with_parents (Path.get_dirname (path), 0700) != 0)
            throw new IOError.FAILED ("Could not create settings directory.");
        FileUtils.set_contents (path, key.to_data ());
    }
    public string text (string group, string name, string fallback) {
        try { return key.get_string (group, name); } catch (Error e) { return fallback; }
    }
    public int number (string group, string name, int fallback, int min, int max) {
        try { return key.get_integer (group, name).clamp (min, max); } catch (Error e) { return fallback; }
    }
    public bool flag (string group, string name, bool fallback = false) {
        try { return key.get_boolean (group, name); } catch (Error e) { return fallback; }
    }
    public string[] folders () {
        string[] result = {};
        foreach (var group in key.get_groups ()) if (group.has_prefix ("Folder ")) result += group;
        return result;
    }
    public string[] members (string folder) {
        try { return key.get_string_list (folder, "apps"); } catch (Error e) { return {}; }
    }
    public void assign (string id, string? folder) {
        foreach (var group in folders ()) {
            string[] kept = {};
            foreach (var member in members (group)) if (member != id) kept += member;
            key.set_string_list (group, "apps", kept);
        }
        if (folder != null) {
            var apps = members (folder); apps += id;
            key.set_string_list (folder, "apps", apps);
        }
    }
    public static StudioPreferences current () {
        var prefs = new StudioPreferences ();
        try { prefs.load (); } catch (Error e) { warning ("Studio settings: %s", e.message); }
        return prefs;
    }
}
